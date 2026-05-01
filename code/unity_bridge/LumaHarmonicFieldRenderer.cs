using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;

/// <summary>
/// LumaHarmonicFieldRenderer
/// ─────────────────────────
/// Fetches /api/unity/edge from the Luma Experience Gateway and renders
/// each harmonic signal as a glowing node in 3D space, arranged on a
/// phi-resonant golden-ratio spiral.
///
/// Assign this to any empty GameObject. Configure in the Inspector:
///   baseUrl         — gateway address (default: http://127.0.0.1:8787)
///   nodePrefab      — a simple sphere prefab with an emissive material
///   refreshSeconds  — how often to re-fetch (default: 3.0)
///   fieldRadius     — radius of the spiral field (default: 6.0)
///
/// Domain colours:
///   crypto   → teal   #45F0C8
///   sports   → gold   #FFD86B
///   infra    → violet #A78BFA
///   other    → white
/// </summary>
public class LumaHarmonicFieldRenderer : MonoBehaviour {

    [Header("Gateway")]
    [SerializeField] private string baseUrl = "http://127.0.0.1:8787";
    [SerializeField] private float refreshSeconds = 3f;

    [Header("Field")]
    [SerializeField] private GameObject nodePrefab;
    [SerializeField] private float fieldRadius = 6f;
    [SerializeField] private float verticalSpread = 4f;
    [SerializeField] private int maxNodes = 50;

    [Header("Colours")]
    [SerializeField] private Color cryptoColor  = new Color(0.271f, 0.941f, 0.784f, 1f);
    [SerializeField] private Color sportsColor  = new Color(1.000f, 0.847f, 0.420f, 1f);
    [SerializeField] private Color infraColor   = new Color(0.655f, 0.545f, 0.980f, 1f);
    [SerializeField] private Color otherColor   = new Color(0.800f, 0.900f, 1.000f, 1f);

    // Golden angle in radians — Φ²
    private const float PHI = 1.6180339887f;
    private const float GOLDEN_ANGLE = 2.399963f; // radians

    // ── Internal state ────────────────────────────────────────────────────────
    private readonly List<NodeInstance> _nodes = new();
    private Coroutine _refreshLoop;
    private float _maxScore = 1f;

    [Serializable]
    private class EdgeNode {
        public int id;
        public string asset;
        public string domain;
        public string signal_type;
        public float edge_pct;
        public float harmonic_score;
        public float curvature;
        public float resonance;
        public float persistence;
        public float phi_bonus;
    }

    [Serializable]
    private class EdgeResponse {
        public string generated_utc;
        public int node_count;
        public float phi;
        public EdgeNode[] nodes;
    }

    private class NodeInstance {
        public GameObject go;
        public EdgeNode data;
        public Vector3 targetPos;
        public float pulsePhase;
    }

    // ── Lifecycle ─────────────────────────────────────────────────────────────
    private void OnEnable() {
        _refreshLoop = StartCoroutine(RefreshLoop());
    }

    private void OnDisable() {
        if (_refreshLoop != null) StopCoroutine(_refreshLoop);
        _refreshLoop = null;
    }

    private IEnumerator RefreshLoop() {
        while (true) {
            yield return FetchAndRender();
            yield return new WaitForSecondsRealtime(Mathf.Max(0.5f, refreshSeconds));
        }
    }

    private IEnumerator FetchAndRender() {
        var url = baseUrl.TrimEnd('/') + "/api/unity/edge";
        using var req = UnityWebRequest.Get(url);
        yield return req.SendWebRequest();

        if (req.result != UnityWebRequest.Result.Success) {
            Debug.LogWarning("[LumaHarmonic] fetch failed: " + req.error);
            yield break;
        }

        EdgeResponse resp;
        try {
            resp = JsonUtility.FromJson<EdgeResponse>(req.downloadHandler.text);
        } catch (Exception ex) {
            Debug.LogWarning("[LumaHarmonic] parse error: " + ex.Message);
            yield break;
        }

        if (resp?.nodes == null || resp.nodes.Length == 0) yield break;

        // Compute max score for normalisation
        _maxScore = 0.001f;
        foreach (var n in resp.nodes) {
            if (n.harmonic_score > _maxScore) _maxScore = n.harmonic_score;
        }

        int count = Mathf.Min(resp.nodes.Length, maxNodes);
        EnsureNodePool(count);

        for (int i = 0; i < count; i++) {
            var data = resp.nodes[i];
            var inst = _nodes[i];
            inst.data = data;
            inst.targetPos = GoldenSpiralPosition(i, count);
            inst.go.SetActive(true);
            ApplyVisuals(inst);
        }

        // Hide excess nodes
        for (int i = count; i < _nodes.Count; i++) {
            _nodes[i].go.SetActive(false);
        }
    }

    // ── Update: animate nodes toward target and pulse ─────────────────────────
    private void Update() {
        float t = Time.time;
        foreach (var inst in _nodes) {
            if (!inst.go.activeSelf || inst.data == null) continue;

            // Smooth position lerp
            inst.go.transform.localPosition = Vector3.Lerp(
                inst.go.transform.localPosition,
                inst.targetPos,
                Time.deltaTime * 2.5f
            );

            // Pulse scale based on harmonic score + phi resonance
            float norm     = inst.data.harmonic_score / _maxScore;
            float phiPulse = Mathf.Sin(t * PHI + inst.pulsePhase) * 0.12f + 1f;
            float edgePop  = 1f + inst.data.edge_pct * 0.003f;
            float scale    = Mathf.Lerp(0.15f, 0.55f, norm) * phiPulse * edgePop;
            inst.go.transform.localScale = Vector3.one * scale;

            // Emission intensity pulsing on material
            var rend = inst.go.GetComponent<Renderer>();
            if (rend != null && rend.material.HasProperty("_EmissionColor")) {
                Color baseCol  = DomainColor(inst.data.domain);
                float emissive = Mathf.Lerp(0.6f, 3.2f, norm) * (0.85f + 0.15f * Mathf.Sin(t * 1.7f + inst.pulsePhase));
                rend.material.SetColor("_EmissionColor", baseCol * emissive);
            }
        }
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    /// Golden-ratio sunflower spiral mapped onto a hemisphere
    private Vector3 GoldenSpiralPosition(int i, int total) {
        float theta  = i * GOLDEN_ANGLE;
        float normR  = Mathf.Sqrt((float)(i + 0.5f) / total);
        float radius = normR * fieldRadius;
        float height = Mathf.Lerp(-verticalSpread * 0.5f, verticalSpread * 0.5f, normR);

        return new Vector3(
            Mathf.Cos(theta) * radius,
            height,
            Mathf.Sin(theta) * radius
        );
    }

    private void ApplyVisuals(NodeInstance inst) {
        if (inst.data == null) return;
        inst.pulsePhase = inst.data.id * 0.618f; // stagger via phi
        var rend = inst.go.GetComponent<Renderer>();
        if (rend == null) return;
        Color c = DomainColor(inst.data.domain);
        rend.material.color = c;
        if (rend.material.HasProperty("_EmissionColor")) {
            rend.material.EnableKeyword("_EMISSION");
            rend.material.SetColor("_EmissionColor", c * 1.5f);
        }

        // Optional: name the node in the hierarchy for debugging
        inst.go.name = $"HarmonicNode_{inst.data.domain}_{inst.data.asset}";
    }

    private void EnsureNodePool(int count) {
        while (_nodes.Count < count) {
            var go = nodePrefab != null
                ? Instantiate(nodePrefab, transform)
                : CreateDefaultSphere();
            _nodes.Add(new NodeInstance { go = go, pulsePhase = _nodes.Count * 0.618f });
        }
    }

    private GameObject CreateDefaultSphere() {
        var go = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        go.transform.SetParent(transform, false);
        go.transform.localScale = Vector3.one * 0.3f;
        // Remove collider — purely visual
        var col = go.GetComponent<Collider>();
        if (col != null) Destroy(col);
        // Assign a new emissive material
        var mat = new Material(Shader.Find("Standard"));
        mat.EnableKeyword("_EMISSION");
        go.GetComponent<Renderer>().material = mat;
        return go;
    }

    private Color DomainColor(string domain) {
        return domain switch {
            "crypto" => cryptoColor,
            "sports" => sportsColor,
            "infra"  => infraColor,
            _        => otherColor,
        };
    }
}
