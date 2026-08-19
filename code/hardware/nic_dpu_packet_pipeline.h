#ifndef LUMENCORE_NIC_DPU_PACKET_PIPELINE_H
#define LUMENCORE_NIC_DPU_PACKET_PIPELINE_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

enum {
    LC_ETHERTYPE_IPV4 = 0x0800,
    LC_ETHERTYPE_VLAN = 0x8100,
    LC_IPPROTO_ANY = 0,
    LC_IPPROTO_TCP = 6,
    LC_IPPROTO_UDP = 17
};

typedef enum {
    LC_PARSE_OK = 0,
    LC_PARSE_NON_IPV4 = 1,
    LC_PARSE_TRUNCATED = 2,
    LC_PARSE_MALFORMED = 3
} lc_parse_status_t;

typedef enum {
    LC_ACTION_PASS = 0,
    LC_ACTION_DROP = 1,
    LC_ACTION_QUEUE = 2
} lc_action_t;

typedef enum {
    LC_REASON_DEFAULT = 0,
    LC_REASON_RULE = 1,
    LC_REASON_INVALID_FRAME = 2,
    LC_REASON_NON_IPV4 = 3
} lc_reason_t;

typedef struct {
    uint16_t ether_type;
    uint16_t vlan_id;
    uint8_t ip_protocol;
    uint8_t dscp;
    uint8_t ttl;
    uint32_t source_ipv4;
    uint32_t destination_ipv4;
    uint16_t source_port;
    uint16_t destination_port;
    bool vlan_present;
    bool fragmented;
    bool ports_valid;
} lc_packet_view_t;

typedef struct {
    uint8_t ip_protocol;
    uint16_t destination_port;
    lc_action_t action;
    uint16_t queue_id;
} lc_rule_t;

typedef struct {
    lc_action_t action;
    lc_reason_t reason;
    uint16_t queue_id;
    lc_parse_status_t parse_status;
} lc_decision_t;

typedef struct {
    uint64_t packets_seen;
    uint64_t packets_parsed;
    uint64_t packets_non_ipv4;
    uint64_t packets_truncated;
    uint64_t packets_malformed;
    uint64_t packets_passed;
    uint64_t packets_dropped;
    uint64_t packets_queued;
} lc_pipeline_counters_t;

lc_parse_status_t lc_parse_packet(
    const uint8_t *frame,
    size_t frame_length,
    lc_packet_view_t *view
);

lc_decision_t lc_classify_packet(
    const lc_packet_view_t *view,
    lc_parse_status_t parse_status,
    const lc_rule_t *rules,
    size_t rule_count
);

lc_decision_t lc_process_packet(
    const uint8_t *frame,
    size_t frame_length,
    const lc_rule_t *rules,
    size_t rule_count,
    lc_pipeline_counters_t *counters
);

#endif
