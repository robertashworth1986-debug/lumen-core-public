#include "nic_dpu_packet_pipeline.h"

#include <string.h>

static uint16_t read_be16(const uint8_t *bytes) {
    return (uint16_t)(((uint16_t)bytes[0] << 8U) | (uint16_t)bytes[1]);
}

static uint32_t read_be32(const uint8_t *bytes) {
    return ((uint32_t)bytes[0] << 24U) |
           ((uint32_t)bytes[1] << 16U) |
           ((uint32_t)bytes[2] << 8U) |
           (uint32_t)bytes[3];
}

lc_parse_status_t lc_parse_packet(
    const uint8_t *frame,
    size_t frame_length,
    lc_packet_view_t *view
) {
    size_t layer3_offset = 14U;
    size_t ip_header_length;
    size_t transport_offset;
    size_t transport_length;
    uint16_t total_length;
    uint16_t flags_fragment;
    uint16_t ether_type;
    uint8_t version_ihl;

    if (frame == NULL || view == NULL) {
        return LC_PARSE_MALFORMED;
    }
    memset(view, 0, sizeof(*view));
    if (frame_length < 14U) {
        return LC_PARSE_TRUNCATED;
    }

    ether_type = read_be16(frame + 12U);
    if (ether_type == LC_ETHERTYPE_VLAN) {
        if (frame_length < 18U) {
            return LC_PARSE_TRUNCATED;
        }
        view->vlan_present = true;
        view->vlan_id = (uint16_t)(read_be16(frame + 14U) & 0x0FFFU);
        ether_type = read_be16(frame + 16U);
        layer3_offset = 18U;
    }
    view->ether_type = ether_type;
    if (ether_type != LC_ETHERTYPE_IPV4) {
        return LC_PARSE_NON_IPV4;
    }
    if (frame_length < layer3_offset + 20U) {
        return LC_PARSE_TRUNCATED;
    }

    version_ihl = frame[layer3_offset];
    if ((version_ihl >> 4U) != 4U || (version_ihl & 0x0FU) < 5U) {
        return LC_PARSE_MALFORMED;
    }
    ip_header_length = (size_t)(version_ihl & 0x0FU) * 4U;
    if (frame_length < layer3_offset + ip_header_length) {
        return LC_PARSE_TRUNCATED;
    }

    total_length = read_be16(frame + layer3_offset + 2U);
    if ((size_t)total_length < ip_header_length) {
        return LC_PARSE_MALFORMED;
    }
    if (frame_length < layer3_offset + (size_t)total_length) {
        return LC_PARSE_TRUNCATED;
    }

    view->dscp = (uint8_t)(frame[layer3_offset + 1U] >> 2U);
    view->ttl = frame[layer3_offset + 8U];
    view->ip_protocol = frame[layer3_offset + 9U];
    view->source_ipv4 = read_be32(frame + layer3_offset + 12U);
    view->destination_ipv4 = read_be32(frame + layer3_offset + 16U);
    flags_fragment = read_be16(frame + layer3_offset + 6U);
    view->fragmented = (flags_fragment & 0x3FFFU) != 0U;
    if (view->fragmented) {
        return LC_PARSE_OK;
    }

    transport_offset = layer3_offset + ip_header_length;
    transport_length = (size_t)total_length - ip_header_length;
    if (view->ip_protocol == LC_IPPROTO_TCP) {
        size_t tcp_header_length;
        if (transport_length < 20U) {
            return LC_PARSE_MALFORMED;
        }
        tcp_header_length = (size_t)(frame[transport_offset + 12U] >> 4U) * 4U;
        if (tcp_header_length < 20U || tcp_header_length > transport_length) {
            return LC_PARSE_MALFORMED;
        }
        view->source_port = read_be16(frame + transport_offset);
        view->destination_port = read_be16(frame + transport_offset + 2U);
        view->ports_valid = true;
    } else if (view->ip_protocol == LC_IPPROTO_UDP) {
        uint16_t udp_length;
        if (transport_length < 8U) {
            return LC_PARSE_MALFORMED;
        }
        udp_length = read_be16(frame + transport_offset + 4U);
        if (udp_length < 8U || (size_t)udp_length > transport_length) {
            return LC_PARSE_MALFORMED;
        }
        view->source_port = read_be16(frame + transport_offset);
        view->destination_port = read_be16(frame + transport_offset + 2U);
        view->ports_valid = true;
    }
    return LC_PARSE_OK;
}

lc_decision_t lc_classify_packet(
    const lc_packet_view_t *view,
    lc_parse_status_t parse_status,
    const lc_rule_t *rules,
    size_t rule_count
) {
    lc_decision_t decision = {LC_ACTION_PASS, LC_REASON_DEFAULT, 0U, parse_status};
    size_t index;

    if (parse_status == LC_PARSE_TRUNCATED || parse_status == LC_PARSE_MALFORMED) {
        decision.action = LC_ACTION_DROP;
        decision.reason = LC_REASON_INVALID_FRAME;
        return decision;
    }
    if (parse_status == LC_PARSE_NON_IPV4) {
        decision.reason = LC_REASON_NON_IPV4;
        return decision;
    }
    if (view == NULL || (rule_count > 0U && rules == NULL)) {
        decision.action = LC_ACTION_DROP;
        decision.reason = LC_REASON_INVALID_FRAME;
        decision.parse_status = LC_PARSE_MALFORMED;
        return decision;
    }

    for (index = 0U; index < rule_count; ++index) {
        bool protocol_match = rules[index].ip_protocol == LC_IPPROTO_ANY ||
                              rules[index].ip_protocol == view->ip_protocol;
        bool port_match = rules[index].destination_port == 0U ||
                          (view->ports_valid &&
                           rules[index].destination_port == view->destination_port);
        if (protocol_match && port_match) {
            decision.action = rules[index].action;
            decision.reason = LC_REASON_RULE;
            decision.queue_id = rules[index].queue_id;
            return decision;
        }
    }
    return decision;
}

lc_decision_t lc_process_packet(
    const uint8_t *frame,
    size_t frame_length,
    const lc_rule_t *rules,
    size_t rule_count,
    lc_pipeline_counters_t *counters
) {
    lc_packet_view_t view;
    lc_parse_status_t status;
    lc_decision_t decision;

    status = lc_parse_packet(frame, frame_length, &view);
    decision = lc_classify_packet(&view, status, rules, rule_count);
    if (counters == NULL) {
        return decision;
    }

    counters->packets_seen += 1U;
    if (status == LC_PARSE_OK) {
        counters->packets_parsed += 1U;
    } else if (status == LC_PARSE_NON_IPV4) {
        counters->packets_non_ipv4 += 1U;
    } else if (status == LC_PARSE_TRUNCATED) {
        counters->packets_truncated += 1U;
    } else {
        counters->packets_malformed += 1U;
    }

    if (decision.action == LC_ACTION_PASS) {
        counters->packets_passed += 1U;
    } else if (decision.action == LC_ACTION_DROP) {
        counters->packets_dropped += 1U;
    } else {
        counters->packets_queued += 1U;
    }
    return decision;
}
