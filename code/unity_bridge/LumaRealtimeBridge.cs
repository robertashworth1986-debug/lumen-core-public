using System;
using System.Collections;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;

[Serializable]
public class LumaGatewayConfig {
    public string baseUrl = "http://127.0.0.1:8787";
    public float pollIntervalSec = 2.0f;
}

public class LumaRealtimeBridge : MonoBehaviour {
    [SerializeField] private string baseUrl = "http://127.0.0.1:8787";
    [SerializeField] private float pollIntervalSec = 2.0f;

    public event Action<string> OnSnapshotJson;
    public event Action<string> OnError;

    private Coroutine _pollRoutine;

    private void OnEnable() {
        _pollRoutine = StartCoroutine(PollSnapshotLoop());
    }

    private void OnDisable() {
        if (_pollRoutine != null) {
            StopCoroutine(_pollRoutine);
            _pollRoutine = null;
        }
    }

    public void Configure(LumaGatewayConfig config) {
        if (config == null) return;
        baseUrl = config.baseUrl;
        pollIntervalSec = Mathf.Max(0.5f, config.pollIntervalSec);
    }

    private IEnumerator PollSnapshotLoop() {
        var wait = new WaitForSecondsRealtime(Mathf.Max(0.5f, pollIntervalSec));
        while (true) {
            yield return FetchSnapshot();
            yield return wait;
        }
    }

    private IEnumerator FetchSnapshot() {
        var url = baseUrl.TrimEnd('/') + "/api/snapshot";
        using var req = UnityWebRequest.Get(url);
        yield return req.SendWebRequest();
        if (req.result == UnityWebRequest.Result.Success) {
            OnSnapshotJson?.Invoke(req.downloadHandler.text);
        } else {
            OnError?.Invoke(req.error ?? "unknown_error");
        }
    }

    public void SendSceneCue(string cue, float intensity = 0.5f, string scene = "core") {
        StartCoroutine(PostSceneCue(cue, intensity, scene));
    }

    public void SendSessionEvent(string eventName, string source = "unity", string detailJson = "{}") {
        StartCoroutine(PostSessionEvent(eventName, source, detailJson));
    }

    private IEnumerator PostSceneCue(string cue, float intensity, string scene) {
        var url = baseUrl.TrimEnd('/') + "/api/scene/cue";
        var payload = "{\"scene\":\"" + scene + "\",\"cue\":\"" + cue + "\",\"intensity\":" + intensity.ToString("0.00") + "}";
        using var req = new UnityWebRequest(url, "POST");
        var bodyRaw = Encoding.UTF8.GetBytes(payload);
        req.uploadHandler = new UploadHandlerRaw(bodyRaw);
        req.downloadHandler = new DownloadHandlerBuffer();
        req.SetRequestHeader("Content-Type", "application/json");
        yield return req.SendWebRequest();
    }

    private IEnumerator PostSessionEvent(string eventName, string source, string detailJson) {
        var url = baseUrl.TrimEnd('/') + "/api/session/event";
        var payload = "{\"event\":\"" + eventName + "\",\"source\":\"" + source + "\",\"detail\":" + detailJson + "}";
        using var req = new UnityWebRequest(url, "POST");
        var bodyRaw = Encoding.UTF8.GetBytes(payload);
        req.uploadHandler = new UploadHandlerRaw(bodyRaw);
        req.downloadHandler = new DownloadHandlerBuffer();
        req.SetRequestHeader("Content-Type", "application/json");
        yield return req.SendWebRequest();
    }
}
