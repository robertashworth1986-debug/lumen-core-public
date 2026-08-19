#include "nic_dpu_packet_pipeline.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define REQUIRE(condition)                                                       \
    do {                                                                         \
        if (!(condition)) {                                                      \
            fprintf(stderr, "REQUIRE failed at %s:%d: %s\n",                  \
                    __FILE__, __LINE__, #condition);                             \
            exit(EXIT_FAILURE);                                                  \
        }                                                                        \
    } while (0)

static void write_be16(uint8_t *bytes, uint16_t value) {
    bytes[0] = (uint8_t)(value >> 8U);
    bytes[1] = (uint8_t)(value & 0xFFU);
}

static size_t build_ipv4_packet(
    uint8_t *frame,
    bool vlan,
    uint8_t protocol,
    uint16_t source_port,
    uint16_t destination_port,
    uint16_t fragment_flags
) {
    size_t layer3 = vlan ? 18U : 14U;
    size_t transport = layer3 + 20U;
    size_t layer4_length = protocol == LC_IPPROTO_TCP ? 20U : 8U;
    size_t frame_length = transport + layer4_length;

    memset(frame, 0, 96U);
    frame[0] = 0x02U;
    frame[6] = 0x06U;
    if (vlan) {
        write_be16(frame + 12U, LC_ETHERTYPE_VLAN);
        write_be16(frame + 14U, 37U);
        write_be16(frame + 16U, LC_ETHERTYPE_IPV4);
    } else {
        write_be16(frame + 12U, LC_ETHERTYPE_IPV4);
    }
    frame[layer3] = 0x45U;
    frame[layer3 + 1U] = 0xB8U;
    write_be16(frame + layer3 + 2U, (uint16_t)(20U + layer4_length));
    write_be16(frame + layer3 + 6U, fragment_flags);
    frame[layer3 + 8U] = 64U;
    frame[layer3 + 9U] = protocol;
    frame[layer3 + 12U] = 10U;
    frame[layer3 + 15U] = 1U;
    frame[layer3 + 16U] = 10U;
    frame[layer3 + 19U] = 2U;
    write_be16(frame + transport, source_port);
    write_be16(frame + transport + 2U, destination_port);
    if (protocol == LC_IPPROTO_TCP) {
        frame[transport + 12U] = 0x50U;
    } else {
        write_be16(frame + transport + 4U, (uint16_t)layer4_length);
    }
    return frame_length;
}

static void test_udp_vlan_queue(void) {
    uint8_t frame[96];
    lc_packet_view_t view;
    lc_rule_t rules[] = {{LC_IPPROTO_UDP, 53U, LC_ACTION_QUEUE, 7U}};
    size_t length = build_ipv4_packet(frame, true, LC_IPPROTO_UDP, 40000U, 53U, 0U);
    lc_parse_status_t status = lc_parse_packet(frame, length, &view);
    lc_decision_t decision = lc_classify_packet(&view, status, rules, 1U);
    REQUIRE(status == LC_PARSE_OK);
    REQUIRE(view.vlan_present && view.vlan_id == 37U);
    REQUIRE(view.dscp == 46U && view.ttl == 64U);
    REQUIRE(view.ports_valid && view.destination_port == 53U);
    REQUIRE(decision.action == LC_ACTION_QUEUE && decision.queue_id == 7U);
}

static void test_tcp_drop_rule(void) {
    uint8_t frame[96];
    lc_packet_view_t view;
    lc_rule_t rules[] = {{LC_IPPROTO_TCP, 22U, LC_ACTION_DROP, 0U}};
    size_t length = build_ipv4_packet(frame, false, LC_IPPROTO_TCP, 51000U, 22U, 0U);
    lc_parse_status_t status = lc_parse_packet(frame, length, &view);
    lc_decision_t decision = lc_classify_packet(&view, status, rules, 1U);
    REQUIRE(status == LC_PARSE_OK && view.ports_valid);
    REQUIRE(decision.action == LC_ACTION_DROP && decision.reason == LC_REASON_RULE);
}

static void test_default_pass(void) {
    uint8_t frame[96];
    lc_packet_view_t view;
    lc_rule_t rules[] = {{LC_IPPROTO_TCP, 22U, LC_ACTION_DROP, 0U}};
    size_t length = build_ipv4_packet(frame, false, LC_IPPROTO_TCP, 51000U, 443U, 0U);
    lc_parse_status_t status = lc_parse_packet(frame, length, &view);
    lc_decision_t decision = lc_classify_packet(&view, status, rules, 1U);
    REQUIRE(decision.action == LC_ACTION_PASS && decision.reason == LC_REASON_DEFAULT);
}

static void test_truncated_drop(void) {
    uint8_t frame[96];
    lc_pipeline_counters_t counters = {0};
    size_t length = build_ipv4_packet(frame, false, LC_IPPROTO_UDP, 1U, 2U, 0U);
    lc_decision_t decision = lc_process_packet(frame, length - 3U, NULL, 0U, &counters);
    REQUIRE(decision.parse_status == LC_PARSE_TRUNCATED);
    REQUIRE(decision.action == LC_ACTION_DROP);
    REQUIRE(counters.packets_truncated == 1U && counters.packets_dropped == 1U);
}

static void test_malformed_ipv4_drop(void) {
    uint8_t frame[96];
    lc_packet_view_t view;
    size_t length = build_ipv4_packet(frame, false, LC_IPPROTO_UDP, 1U, 2U, 0U);
    frame[14U] = 0x44U;
    REQUIRE(lc_parse_packet(frame, length, &view) == LC_PARSE_MALFORMED);
}

static void test_non_ipv4_pass(void) {
    uint8_t frame[64] = {0};
    lc_pipeline_counters_t counters = {0};
    lc_decision_t decision;
    write_be16(frame + 12U, 0x86DDU);
    decision = lc_process_packet(frame, sizeof(frame), NULL, 0U, &counters);
    REQUIRE(decision.parse_status == LC_PARSE_NON_IPV4);
    REQUIRE(decision.action == LC_ACTION_PASS && decision.reason == LC_REASON_NON_IPV4);
    REQUIRE(counters.packets_non_ipv4 == 1U && counters.packets_passed == 1U);
}

static void test_fragment_ports_are_not_claimed(void) {
    uint8_t frame[96];
    lc_packet_view_t view;
    lc_rule_t rules[] = {{LC_IPPROTO_UDP, 53U, LC_ACTION_DROP, 0U}};
    size_t length = build_ipv4_packet(frame, false, LC_IPPROTO_UDP, 1U, 53U, 0x2000U);
    lc_parse_status_t status = lc_parse_packet(frame, length, &view);
    lc_decision_t decision = lc_classify_packet(&view, status, rules, 1U);
    REQUIRE(status == LC_PARSE_OK && view.fragmented && !view.ports_valid);
    REQUIRE(decision.action == LC_ACTION_PASS);
}

static void run_benchmark(size_t iterations) {
    uint8_t frame[96];
    lc_rule_t rules[] = {
        {LC_IPPROTO_TCP, 22U, LC_ACTION_DROP, 0U},
        {LC_IPPROTO_UDP, 53U, LC_ACTION_QUEUE, 7U}
    };
    lc_pipeline_counters_t counters = {0};
    lc_decision_t decision;
    clock_t start;
    clock_t end;
    double elapsed_seconds;
    size_t index;
    size_t length = build_ipv4_packet(frame, true, LC_IPPROTO_UDP, 40000U, 53U, 0U);

    start = clock();
    for (index = 0U; index < iterations; ++index) {
        decision = lc_process_packet(frame, length, rules, 2U, &counters);
        REQUIRE(decision.action == LC_ACTION_QUEUE);
    }
    end = clock();
    elapsed_seconds = (double)(end - start) / (double)CLOCKS_PER_SEC;
    printf(
        "BENCH packets=%zu elapsed_seconds=%.9f packets_per_second=%.3f queued=%llu\n",
        iterations,
        elapsed_seconds,
        elapsed_seconds > 0.0 ? (double)iterations / elapsed_seconds : 0.0,
        (unsigned long long)counters.packets_queued
    );
}

int main(int argc, char **argv) {
    size_t benchmark_iterations = 0U;
    test_udp_vlan_queue();
    test_tcp_drop_rule();
    test_default_pass();
    test_truncated_drop();
    test_malformed_ipv4_drop();
    test_non_ipv4_pass();
    test_fragment_ports_are_not_claimed();
    printf("TESTS passed=7 failed=0\n");
    if (argc == 3 && strcmp(argv[1], "--benchmark") == 0) {
        benchmark_iterations = (size_t)strtoull(argv[2], NULL, 10);
        if (benchmark_iterations > 0U) {
            run_benchmark(benchmark_iterations);
        }
    }
    return 0;
}
