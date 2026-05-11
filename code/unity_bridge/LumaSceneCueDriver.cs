using UnityEngine;
using System.Globalization;

public class LumaSceneCueDriver : MonoBehaviour {
    [SerializeField] private LumaWsClientBridge wsBridge;
    [SerializeField] private Light pulseLight;
    [SerializeField] private Renderer coreRenderer;
    [SerializeField] private Transform reactiveRoot;
    [SerializeField] private Color calmColor = new Color(0.35f, 0.95f, 0.84f);
    [SerializeField] private Color warningColor = new Color(1f, 0.35f, 0.35f);
    [SerializeField] private Color successColor = new Color(0.36f, 1f, 0.55f);
    [SerializeField] private Color harmonicColor = new Color(0.2f, 0.85f, 1f);
    [SerializeField] private Color institutionalColor = new Color(0.42f, 0.62f, 1f);
    [SerializeField] private Color scenarioAccentColor = new Color(1f, 0.88f, 0.46f);
    [SerializeField] private float scenarioProgressBoost = 0.22f;
    [SerializeField] private float scenarioShakeBoost = 0.14f;
    [SerializeField] private float scenarioScaleBoost = 0.10f;

    private Vector3 _baseScale = Vector3.one;

    private void Awake() {
        if (wsBridge == null) {
            wsBridge = FindObjectOfType<LumaWsClientBridge>();
        }

        if (reactiveRoot == null) {
            reactiveRoot = transform;
        }
        _baseScale = reactiveRoot.localScale;
    }

    private void OnEnable() {
        if (wsBridge == null) return;
        wsBridge.OnSceneCueMessage += HandleCue;
    }

    private void OnDisable() {
        if (wsBridge == null) return;
        wsBridge.OnSceneCueMessage -= HandleCue;
    }

    private void HandleCue(string payload) {
        string cue = ExtractString(payload, "\"cue\":\"");
        string palette = ExtractString(payload, "\"palette\":\"");
        string band = ExtractString(payload, "\"band\":\"");
        float intensity = ExtractFloat(payload, "\"intensity\":", 0.5f);
        float bloom = ExtractFloat(payload, "\"bloom\":", 0.42f);
        float shake = ExtractFloat(payload, "\"shake\":", 0.08f);
        float density = ExtractFloat(payload, "\"density\":", 0.45f);
        int scenarioStep = ExtractInt(payload, "\"scenario_step\":", ExtractInt(payload, "\"sim_step\":", 0));
        int scenarioTotal = ExtractInt(payload, "\"scenario_total_steps\":", ExtractInt(payload, "\"sim_total_steps\":", 0));
        float scenarioProgress = scenarioTotal > 0
            ? Mathf.Clamp01((float)scenarioStep / (float)scenarioTotal)
            : 0f;

        bool warning = cue.Contains("warning") || cue.Contains("critical") || payload.Contains("loss") || palette.Contains("critical");
        Color c = ResolveCueColor(cue, palette, warning);

        float bandBoost = 1f;
        switch (band) {
            case "low":
                bandBoost = 0.85f;
                break;
            case "high":
                bandBoost = 1.18f;
                break;
            case "extreme":
                bandBoost = 1.34f;
                break;
        }
        float adjusted = Mathf.Clamp01(intensity * bandBoost);
        float bloomBoost = Mathf.Lerp(0.92f, 1.36f, Mathf.Clamp01(bloom));
        float densityBoost = Mathf.Clamp01(density);

        if (scenarioProgress > 0f) {
            adjusted = Mathf.Clamp01(adjusted + (scenarioProgress * scenarioProgressBoost));
            shake = Mathf.Clamp01(shake + (scenarioProgress * scenarioShakeBoost));
            densityBoost = Mathf.Clamp01(densityBoost + (scenarioProgress * 0.15f));
            c = Color.Lerp(c, scenarioAccentColor, scenarioProgress * 0.22f);
        }

        if (pulseLight != null) {
            pulseLight.color = c;
            pulseLight.intensity = Mathf.Lerp(0.9f, 5.5f, adjusted) * bloomBoost;
            pulseLight.range = Mathf.Lerp(4f, 16f, densityBoost);
        }

        if (coreRenderer != null && coreRenderer.material != null) {
            coreRenderer.material.EnableKeyword("_EMISSION");
            coreRenderer.material.SetColor("_EmissionColor", c * Mathf.Lerp(0.6f, 3.4f, adjusted));
            float smooth = Mathf.Lerp(0.22f, 0.78f, Mathf.Clamp01(shake + adjusted * 0.35f));
            if (coreRenderer.material.HasProperty("_Glossiness")) {
                coreRenderer.material.SetFloat("_Glossiness", smooth);
            }
            if (coreRenderer.material.HasProperty("_Smoothness")) {
                coreRenderer.material.SetFloat("_Smoothness", smooth);
            }
        }

        if (reactiveRoot != null) {
            float scalePulse = 1f + (adjusted * 0.18f) + (Mathf.Clamp01(shake) * 0.06f) + (scenarioProgress * scenarioScaleBoost);
            reactiveRoot.localScale = _baseScale * scalePulse;
        }
    }

    private Color ResolveCueColor(string cue, string palette, bool warning) {
        if (palette.Contains("critical") || cue.Contains("critical")) return warningColor;
        if (cue.Contains("harmonic") || palette.Contains("harmonic")) return harmonicColor;
        if (cue.Contains("institutional") || palette.Contains("institutional")) return institutionalColor;
        if (cue.Contains("success") || palette.Contains("profit")) return successColor;
        if (warning) return warningColor;
        return calmColor;
    }

    private float ExtractFloat(string payload, string token, float fallback) {
        int idx = payload.IndexOf(token);
        if (idx < 0) return fallback;
        int start = idx + token.Length;
        int end = start;
        while (end < payload.Length && "0123456789.-".IndexOf(payload[end]) >= 0) {
            end += 1;
        }

        if (start >= payload.Length || end <= start) return fallback;

        if (float.TryParse(payload.Substring(start, end - start), NumberStyles.Float, CultureInfo.InvariantCulture, out float value)) {
            return Mathf.Clamp01(value);
        }

        return fallback;
    }

    private int ExtractInt(string payload, string token, int fallback) {
        int idx = payload.IndexOf(token);
        if (idx < 0) return fallback;
        int start = idx + token.Length;
        int end = start;
        while (end < payload.Length && "0123456789-".IndexOf(payload[end]) >= 0) {
            end += 1;
        }

        if (start >= payload.Length || end <= start) return fallback;

        if (int.TryParse(payload.Substring(start, end - start), NumberStyles.Integer, CultureInfo.InvariantCulture, out int value)) {
            return Mathf.Max(0, value);
        }

        return fallback;
    }

    private string ExtractString(string payload, string token) {
        int idx = payload.IndexOf(token);
        if (idx < 0) return string.Empty;

        int start = idx + token.Length;
        int end = start;
        while (end < payload.Length) {
            if (payload[end] == '"' && payload[end - 1] != '\\') {
                break;
            }
            end += 1;
        }

        if (end <= start || end > payload.Length) return string.Empty;
        return payload.Substring(start, end - start).Trim().ToLowerInvariant();
    }
}
