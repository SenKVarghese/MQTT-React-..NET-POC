var builder = DistributedApplication.CreateBuilder(args);
//builder.AddForwardedHeaders();
var pocDB = builder.AddConnectionString("pocDB");
//var onSyteApiDb = builder.AddConnectionString("onSyteApiDb");

//builder.AddForwardedHeaders();

var apiService = builder.AddProject<Projects.POC_WebSocket_Backend>("apiservice").WithReference(pocDB);

var frontend = builder.AddNpmApp("front", "../../v2/flowbite-react-template-vite-main", "dev")
    .WithHttpEndpoint(3000, env: "PORT")
    .WithExternalHttpEndpoints()
     //.WithEnvironment("PORT", "3000")
    .PublishAsDockerFile();
var frontendUrl = frontend.GetEndpoint("http");

builder.Build().Run();