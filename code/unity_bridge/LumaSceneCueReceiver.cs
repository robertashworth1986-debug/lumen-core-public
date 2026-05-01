using System;
using UnityEngine;

[Serializable]
public class SnapshotRoot {
    public string generated_utc;
    public PaperData paper;
    public InfraData infra;
    public ScoutData scout;
}

[Serializable]
public class PaperData {
    public float equity;
    public float net_pnl;
    public int closed_trades;
}

[Serializable]
public class InfraData {
    public string top_lane;
}

[Serializable]
public class ScoutData {
    public string top_artist;
}

public class LumaSceneCueReceiver : MonoBehaviour {
    [SerializeField] private LumaRealtimeBridge realtimeBridge;
    [SerializeField] private Light pulseLight;
    [SerializeField] private Renderer coreRenderer;

    private Color _baseColor = new Color(0.35f, 0.95f, 0.84f);

    private void Awake() {
        if (realtimeBridge == null) {
            realtimeBridge = FindObjectOfType<LumaRealtimeBridge>();
        }
    }

    private void OnEnable() {
        if (realtimeBridge == null) return;
        realtimeBridge.OnSnapshotJson += HandleSnapshot;
        realtimeBridge.OnError += HandleError;
    }

    private void OnDisable() {
        if (realtimeBridge == null) return;
        realtimeBridge.OnSnapshotJson -= HandleSnapshot;
        realtimeBridge.OnError -= HandleError;
    }

    private void HandleSnapshot(string json) {
        var root = JsonUtility.FromJson<SnapshotRoot>(json);
        if (root == null || root.paper == null) return;

        float intensity = Mathf.Clamp01(Mathf.Abs(root.paper.net_pnl) / 100000f);
        var color = root.paper.net_pnl >= 0 ? _baseColor : new Color(1f, 0.35f, 0.35f);

        if (pulseLight != null) {
            pulseLight.intensity = Mathf.Lerp(1.2f, 3.8f, intensity);
            pulseLight.color = color;
        }

        if (coreRenderer != null && coreRenderer.material != null) {
            coreRenderer.material.SetColor("_EmissionColor", color * Mathf.Lerp(0.4f, 2.0f, intensity));
        }
    }

    private void HandleError(string message) {
        Debug.LogWarning("Luma gateway error: " + message);
    }
}
