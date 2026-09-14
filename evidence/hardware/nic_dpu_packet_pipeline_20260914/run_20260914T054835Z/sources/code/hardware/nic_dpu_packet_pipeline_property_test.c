#include "nic_dpu_packet_pipeline.h"

#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_FRAME 65553U
static uint32_t random_state;
static uint64_t case_index;
static uint64_t outcomes[4];
static const uint8_t *current_frame;
static size_t current_length;

static void require_property(int condition, const char *property) {
    if (!condition) {
        FILE *failure = fopen("property_failure_frame.bin", "wb");
        if (failure != NULL) {
            (void)fwrite(current_frame, 1U, current_length, failure);
            (void)fclose(failure);
        }
        fprintf(stderr, "PROPERTY_FAILED case=%" PRIu64 " property=%s length=%zu\n",
                case_index, property, current_length);
        exit(EXIT_FAILURE);
    }
}

static uint32_t next_random(void) {
    uint32_t value = random_state;
    value ^= value << 13U;
    value ^= value >> 17U;
    value ^= value << 5U;
    random_state = value;
    return value;
}

static void write_be16(uint8_t *target, uint16_t value) {
    target[0] = (uint8_t)(value >> 8U);
    target[1] = (uint8_t)value;
}

static size_t make_template(uint8_t *frame) {
    bool vlan = (next_random() & 1U) != 0U;
    bool tcp = (next_random() & 1U) != 0U;
    size_t layer3 = vlan ? 18U : 14U;
    size_t ihl = (5U + next_random() % 11U) * 4U;
    size_t transport_header = tcp ? (5U + next_random() % 11U) * 4U : 8U;
    size_t payload = next_random() % 201U;
    size_t transport = layer3 + ihl;
    size_t length = transport + transport_header + payload;
    memset(frame, 0, length);
    write_be16(frame + 12U, vlan ? LC_ETHERTYPE_VLAN : LC_ETHERTYPE_IPV4);
    if (vlan) {
        write_be16(frame + 14U, (uint16_t)next_random());
        write_be16(frame + 16U, LC_ETHERTYPE_IPV4);
    }
    frame[layer3] = (uint8_t)(0x40U | (ihl / 4U));
    frame[layer3 + 1U] = (uint8_t)next_random();
    frame[layer3 + 8U] = (uint8_t)next_random();
    frame[layer3 + 9U] = tcp ? LC_IPPROTO_TCP : LC_IPPROTO_UDP;
    write_be16(frame + layer3 + 2U, (uint16_t)(length - layer3));
    if ((case_index % 16U) == 1U) {
        write_be16(frame + layer3 + 6U, (uint16_t)(0x2000U | (next_random() & 0x1FFFU)));
    }
    write_be16(frame + transport, (uint16_t)next_random());
    write_be16(frame + transport + 2U, tcp ? 22U : 53U);
    if (tcp) {
        frame[transport + 12U] = (uint8_t)((transport_header / 4U) << 4U);
    } else {
        write_be16(frame + transport + 4U, (uint16_t)(transport_header + payload));
    }
    return length;
}

static void check_frame(const uint8_t *frame, size_t length) {
    lc_packet_view_t first;
    lc_packet_view_t second;
    lc_pipeline_counters_t counters = {0};
    const lc_rule_t rules[] = {
        {LC_IPPROTO_TCP, 22U, LC_ACTION_DROP, 0U},
        {LC_IPPROTO_UDP, 53U, LC_ACTION_QUEUE, 7U}
    };
    lc_parse_status_t status = lc_parse_packet(frame, length, &first);
    lc_parse_status_t again = lc_parse_packet(frame, length, &second);
    lc_decision_t decision = lc_process_packet(frame, length, rules, 2U, &counters);
    require_property(status >= LC_PARSE_OK && status <= LC_PARSE_MALFORMED, "declared_parse_status");
    outcomes[(size_t)status] += 1U;
    require_property(status == again && memcmp(&first, &second, sizeof(first)) == 0, "deterministic_initialized_view");
    require_property(decision.parse_status == status, "parser_pipeline_status_agree");
    require_property(decision.action >= LC_ACTION_PASS && decision.action <= LC_ACTION_QUEUE, "declared_action");
    if (status == LC_PARSE_TRUNCATED || status == LC_PARSE_MALFORMED) {
        require_property(decision.action == LC_ACTION_DROP, "invalid_frames_drop");
    }
    require_property(!first.fragmented || !first.ports_valid, "fragment_ports_unavailable");
    require_property(!first.ports_valid || first.ip_protocol == LC_IPPROTO_TCP || first.ip_protocol == LC_IPPROTO_UDP,
                     "transport_ports_have_supported_protocol");
    require_property(counters.packets_seen == 1U, "one_observed_packet");
    require_property(counters.packets_parsed + counters.packets_non_ipv4 + counters.packets_truncated +
                     counters.packets_malformed == 1U, "parse_counter_partition");
    require_property(counters.packets_passed + counters.packets_dropped + counters.packets_queued == 1U,
                     "action_counter_partition");
}

int main(int argc, char **argv) {
    uint8_t generated[MAX_FRAME];
    uint64_t cases = 500000U;
    uint32_t seed = 20260914U;
    if (argc == 3) {
        cases = (uint64_t)strtoull(argv[1], NULL, 10);
        seed = (uint32_t)strtoul(argv[2], NULL, 10);
    } else if (argc != 1) {
        return EXIT_FAILURE;
    }
    if (cases == 0U || cases > 10000000U || seed == 0U) {
        return EXIT_FAILURE;
    }
    random_state = seed;
    for (case_index = 0U; case_index < cases; ++case_index) {
        size_t length;
        size_t offset = case_index % 3U == 0U ? 0U : (case_index % 3U == 1U ? 1U : 3U);
        uint8_t *allocation;
        uint8_t *frame;
        if (case_index % 4U == 0U) {
            size_t index;
            length = case_index % 4096U == 0U ? MAX_FRAME : next_random() % 257U;
            for (index = 0U; index < length; ++index) {
                generated[index] = (uint8_t)next_random();
            }
        } else {
            length = make_template(generated);
            if (case_index % 4U == 2U) {
                size_t mutation;
                size_t count = 1U + next_random() % 8U;
                for (mutation = 0U; mutation < count; ++mutation) {
                    size_t position = next_random() % length;
                    uint8_t mask = (uint8_t)(1U + next_random() % 255U);
                    generated[position] ^= mask;
                }
            } else if (case_index % 4U == 3U) {
                length = next_random() % (length + 1U);
            }
        }
        allocation = malloc(length + offset == 0U ? 1U : length + offset);
        if (allocation == NULL) {
            return EXIT_FAILURE;
        }
        frame = allocation + offset;
        memcpy(frame, generated, length);
        current_frame = frame;
        current_length = length;
        check_frame(frame, length);
        require_property(memcmp(frame, generated, length) == 0, "input_bytes_preserved");
        free(allocation);
    }
    printf("PROPERTY cases=%" PRIu64 " seed=%" PRIu32 " ok=%" PRIu64 " non_ipv4=%" PRIu64
           " truncated=%" PRIu64 " malformed=%" PRIu64 " failed=0\n",
           cases, seed, outcomes[0], outcomes[1], outcomes[2], outcomes[3]);
    return EXIT_SUCCESS;
}
