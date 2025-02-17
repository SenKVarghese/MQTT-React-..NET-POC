using Microsoft.EntityFrameworkCore;
using POC_WebSocket_Backend.Models;

namespace POC_WebSocket_Backend.Data
{
    public class ApplicationDbContext : DbContext
    {
        public ApplicationDbContext(DbContextOptions<ApplicationDbContext> options) : base(options)
        {
        }

        public DbSet<Station> Stations { get; set; }
    }
}
