using System.Net.WebSockets;
using System.Collections.Concurrent;

namespace WebSocketBackend.Services
{
    public class WebSocketConnectionManager
    {
        private readonly ConcurrentDictionary<string, WebSocket> _sockets = new();

        public string AddSocket(WebSocket socket)
        {
            var connectionId = Guid.NewGuid().ToString();
            _sockets.TryAdd(connectionId, socket);
            return connectionId;
        }

        public async Task RemoveSocket(string id)
        {
            _sockets.TryRemove(id, out var socket);
            if (socket != null)
            {
                await socket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Connection closed", CancellationToken.None);
            }
        }

        public ConcurrentDictionary<string, WebSocket> GetAllSockets() => _sockets;
    }
}
