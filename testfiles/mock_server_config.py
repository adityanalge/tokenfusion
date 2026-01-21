import json
import random

def generate_huge_config(file_path, num_servers=5000):
    servers = []
    regions = ["us-east-1", "us-west-2", "eu-central-1", "ap-southeast-1"]
    statuses = ["active", "maintenance", "offline", "provisioning"]
    
    for i in range(num_servers):
        server = {
            "server_id": f"srv-{i:06d}",
            "hostname": f"node-{random.choice(regions)}-{i:04d}",
            "ip_address": f"{random.randint(10, 192)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}",
            "status": random.choice(statuses),
            "specs": {
                "cpu_cores": random.choice([8, 16, 32, 64]),
                "ram_gb": random.choice([32, 64, 128, 256]),
                "storage": [
                    {"type": "SSD", "size_gb": random.randint(256, 1024)},
                    {"type": "HDD", "size_gb": random.randint(1024, 8192)}
                ]
            },
            "tags": [random.choice(regions), "enterprise", "v3-arch"],
            "uptime_seconds": random.randint(0, 10000000),
            "metadata": {
                "owner": "infrastructure-team",
                "department": "core-services",
                "cost_center": f"CC-{random.randint(100, 999)}",
                "notes": "Generated for high-load tokenization test cases."
            }
        }
        servers.append(server)

    with open(file_path, 'w') as f:
        json.dump(servers, f, indent=2)
    
    print(f"File saved to {file_path} with {num_servers} server entries.")

if __name__ == "__main__":
    generate_huge_config("server_configs_huge.json", num_servers=4500)