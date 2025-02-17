using System.ComponentModel.DataAnnotations;

namespace POC_WebSocket_Backend.Models
{
    public class Station
    {
        [Key]
        public int Id { get; set; }

        [Required]
        public string Name { get; set; } = string.Empty;

        [Required]
        public string Location { get; set; } = string.Empty;

        [Required]
        public string Status { get; set; } = "Active"; // Default status is Active
    }
}
