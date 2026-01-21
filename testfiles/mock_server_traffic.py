import json
import random
import os

def generate_server_metrics(num_servers=1000):
    # Detect the directory where this script is located
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, "server_metrics.json")
    
    regions = ["us-east-1", "us-west-2", "eu-central-1", "ap-southeast-1"]
    servers = []

    print(f"Generating metrics for {num_servers} servers...")

    for i in range(num_servers):
        region = random.choice(regions)
        
        server = {
            "server_id": f"srv-{i:06d}",
            "hostname": f"node-{region}-{i:04d}",
            "ip_address": f"{random.randint(10, 192)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}",
            "status": random.choice(["active", "active", "active", "high-load"]), # Mostly active
            "metrics": {
                "cpu_utilization_pct": round(random.uniform(2.0, 98.0), 2),
                "ram_usage_gb": round(random.uniform(4.0, 128.0), 2),
                "storage_used_pct": round(random.uniform(10.0, 95.0), 2),
                "network_traffic": {
                    "incoming_mbps": round(random.uniform(10.0, 1000.0), 2),
                    "outgoing_mbps": round(random.uniform(50.0, 5000.0), 2),
                    "active_connections": random.randint(100, 50000)
                }
            },
            "tags": [
                region,
                "production",
                "monitoring-enabled"
            ],
            "uptime_seconds": random.randint(0, 5000000),
            "health_score": round(random.uniform(0.7, 1.0), 2)
        }
        servers.append(server)

    # Write the file to the same directory as the script
    with open(file_path, 'w') as f:
        json.dump(servers, f, indent=2)
    
    print(f"Success! File created at: {file_path}")

if __name__ == "__main__":
    generate_server_metrics()