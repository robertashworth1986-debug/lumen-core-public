using System;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine;

public class LumaWsClientBridge : MonoBehaviour {
    [SerializeField] private string wsUrl = "ws://127.0.0.1:8787/ws/live";
    [SerializeField] private bool autoConnect = true;

    public event Action<string> OnRawMessage;
    public event Action<string> OnSnapshotMessage;
    public event Action<string> OnSceneCueMessage;
    public event Action<string> OnSocketError;

    private ClientWebSocket _socket;
    private CancellationTokenSource _cts;

    private async void OnEnable() {
        if (autoConnect) {
            await ConnectAsync();
        }
    }

    private async void OnDisable() {
        await DisconnectAsync();
    }

    public async Task ConnectAsync() {
        if (_socket != null && _socket.State == WebSocketState.Open) {
            return;
        }

        _cts = new CancellationTokenSource();
        _socket = new ClientWebSocket();

        try {
            await _socket.ConnectAsync(new Uri(wsUrl), _cts.Token);
            _ = ReceiveLoop(_cts.Token);
            await SendTextAsync("hello");
        } catch (Exception ex) {
            OnSocketError?.Invoke(ex.Message);
            Debug.LogWarning("Luma WS connect failed: " + ex.Message);
        }
    }

    public async Task DisconnectAsync() {
        if (_cts != null) {
            _cts.Cancel();
            _cts.Dispose();
            _cts = null;
        }

        if (_socket != null) {
            try {
                if (_socket.State == WebSocketState.Open) {
                    await _socket.CloseAsync(WebSocketCloseStatus.NormalClosure, "shutdown", CancellationToken.None);
                }
            } catch {
                // Ignore close errors.
            }
            _socket.Dispose();
            _socket = null;
        }
    }

    public async Task SendTextAsync(string message) {
        if (_socket == null || _socket.State != WebSocketState.Open) {
            return;
        }

        var bytes = Encoding.UTF8.GetBytes(message);
        await _socket.SendAsync(new ArraySegment<byte>(bytes), WebSocketMessageType.Text, true, _cts.Token);
    }

    private async Task ReceiveLoop(CancellationToken token) {
        var buffer = new byte[8192];

        while (!token.IsCancellationRequested && _socket != null && _socket.State == WebSocketState.Open) {
            try {
                var result = await _socket.ReceiveAsync(new ArraySegment<byte>(buffer), token);
                if (result.MessageType == WebSocketMessageType.Close) {
                    break;
                }

                var text = Encoding.UTF8.GetString(buffer, 0, result.Count);
                OnRawMessage?.Invoke(text);

                if (text.Contains("\"type\": \"snapshot\"") || text.Contains("\"type\":\"snapshot\"")) {
                    OnSnapshotMessage?.Invoke(text);
                } else if (text.Contains("\"type\": \"scene_cue\"") || text.Contains("\"type\":\"scene_cue\"")) {
                    OnSceneCueMessage?.Invoke(text);
                }
            } catch (Exception ex) {
                OnSocketError?.Invoke(ex.Message);
                Debug.LogWarning("Luma WS receive failed: " + ex.Message);
                break;
            }
        }
    }
}
