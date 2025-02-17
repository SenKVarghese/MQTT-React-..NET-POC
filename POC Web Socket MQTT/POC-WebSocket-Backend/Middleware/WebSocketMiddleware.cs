using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using WebSocketBackend.Services;

namespace WebSocketBackend.Middleware
{
    public class WebSocketMiddleware
    {
        private readonly RequestDelegate _next;
        private readonly WebSocketConnectionManager _manager;

        public WebSocketMiddleware(RequestDelegate next, WebSocketConnectionManager manager)
        {
            _next = next;
            _manager = manager;
        }

        public async Task InvokeAsync(HttpContext context)
        {
            if (context.Request.Path == "/ws")
            {
                if (context.WebSockets.IsWebSocketRequest)
                {
                    using var webSocket = await context.WebSockets.AcceptWebSocketAsync();
                    var connectionId = _manager.AddSocket(webSocket);
                    //await HandleWebSocketAsync(webSocket);
                    await SendStationData(webSocket);
                    await _manager.RemoveSocket(connectionId);
                }
                else
                {
                    context.Response.StatusCode = 400;
                }
            }
            else
            {
                await _next(context);
            }
        }
        private async Task SendStationData(WebSocket webSocket)
        {
            var random = new Random();
            while (webSocket.State == WebSocketState.Open)
            {
                var data = new
                {
                    allUsers = random.Next(50, 100),
                    onlineUsers = random.Next(20, 50),
                    offlineUsers = random.Next(10, 20),
                    status = random.Next(0, 2) == 0 ? "Online" : "Offline"
                };

                var json = JsonSerializer.Serialize(data);
                var bytes = Encoding.UTF8.GetBytes(json);
                await webSocket.SendAsync(new ArraySegment<byte>(bytes), WebSocketMessageType.Text, true, CancellationToken.None);

                // Wait for a random interval (max 20 seconds)
                await Task.Delay(random.Next(10, 500));
            }
        }
        private async Task HandleWebSocketAsync(WebSocket webSocket)
        {
            var buffer = new byte[1024 * 4];

            while (webSocket.State == WebSocketState.Open)
            {
                var result = await webSocket.ReceiveAsync(new ArraySegment<byte>(buffer), CancellationToken.None);
                if (result.MessageType == WebSocketMessageType.Close)
                {
                    await webSocket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Closing", CancellationToken.None);
                }
                else
                {
                    var receivedText = Encoding.UTF8.GetString(buffer, 0, result.Count);
                    Console.WriteLine($"Received: {receivedText}");

                    var echoText = $"Echo: {receivedText}";
                    var echoBytes = Encoding.UTF8.GetBytes(echoText);

                    await webSocket.SendAsync(new ArraySegment<byte>(echoBytes), WebSocketMessageType.Text, true, CancellationToken.None);
                }
            }
        }
    }

    public static class WebSocketMiddlewareExtensions
    {
        public static IApplicationBuilder UseWebSocketMiddleware(this IApplicationBuilder builder)
        {
            return builder.UseMiddleware<WebSocketMiddleware>();
        }
    }
}
