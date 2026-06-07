# Distributed Price & Availability Engine (Flash Sale Architecture)

A highly available, resilient, containerized Product Pricing & Availability API engineered to handle massive read spikes and immediate cache invalidation during high-concurrency traffic events (e.g., Flash Sales). This system segregates Read and Write workloads, implements multi-layered caching, utilizes Nginx load balancing across horizontally scaled application instances, and features zero-downtime automated provisioning via Ansible.

---

## 🏗️ Architectural Design & System Topology

The architecture is built inside-out to enforce **Command Query Responsibility Segregation (CQRS)** at the data layer, ensuring database deadlocks are prevented during intense concurrent traffic.


```text
              [ Client / User Browser ]
                         │
                  HTTP / Port 80
                         ▼
                [ Nginx Reverse Proxy ]
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼  (Round-Robin Load Balancing)
   [ App Node 1 ]  [ App Node 2 ]  [ App Node 3 ]  (FastAPI / Async Python)
         │               │               │
         ├───────────────┴───────────────┤
         │  (1) Check Cache              │ (2) Admin Price Update
         ▼                               ▼
   [ Redis Cache ]               [ MySQL Master ]
         │                               │
         │ (Cache Miss)                  │ (Binary Log Async Replication)
         ▼                               ▼
 [ MySQL Replica ] ◄─────────────────────┘

```

### End-to-End Workflows

1. **The Fast Read Path (99% of Traffic):** Requests hit the **Nginx** load balancer, which forwards them to a horizontally scaled **FastAPI Application Node**. The app queries the **Redis Cache Instance** (In-Memory, `allkeys-lru` eviction policy). 
   * **Cache Hit:** Data returns instantly ($\le 2\text{ms}$).
   * **Cache Miss:** The app queries the read-only **MySQL Replica**, updates Redis with an explicit Time-To-Live (TTL) of 3600 seconds, and returns the payload.

2. **The Controlled Write/Admin Path:** Internal internal departments or vendors push price updates to `/admin/products/{id}`. The application writes directly to the **MySQL Master Instance**. 

3. **Strict Cache Invalidation:** Upon a successful commit to the MySQL Master, the application executes an immediate active invalidation rule (`redis.delete(product_id)`). The subsequent read request triggers a cache miss, pulling fresh data from the replica and eliminating the stale-data propagation window.

---

## 📂 Repository Structure

```text
blitz/
├── ansible/
│   ├── inventory.ini         # Target host definition (e.g., Hetzner CCX23 Dedicated VPS)
│   └── deploy.yml            # Automation Playbook (OS hardening, Docker provisioning, app lifecycle)
├── backend/
│   ├── Dockerfile            # Lightweight multi-stage Python 3.11 environment
│   ├── main.py               # Asynchronous FastAPI implementation with Redis & MySQL drivers
│   └── requirements.txt      # Pin-point production dependencies (fastapi, uvicorn, redis, aiomysql)
├── frontend/
│   └── index.html            # Single-Page App (Vanilla JS Fetch API) simulating Customer & Vendor portals
├── nginx/
│   └── nginx.conf            # High-performance reverse proxy & dynamic upstream balancing
└── docker-compose.yml        # Multi-container multi-network orchestration blueprint

```

---

## 🛠️ Infrastructure Automation (Ansible)

The entire server environment on the Hetzner target instance is provisioned idempotently from a local control node via Ansible. Manual configuration (`SSH` + naked commands) is completely banned.

### Playbook Tasks Managed Automatically:

1. **Host Hardening:** Cache updates via `apt`, installation of core dependencies (`curl`, `git`, `python3-pip`), and configuration of **UFW (Uncomplicated Firewall)** to strictly restrict inputs to ports `22` (SSH), `80` (HTTP), and `443` (HTTPS).
2. **Container Engine Setup:** Secure installation of Docker CE and the `docker-compose-plugin`, handling repository additions and user group permissions dynamically.
3. **Application Lifecycle:** Transfers configuration matrices, injects environment secrets securely via templating, and provisions the containerized architecture, establishing horizontal application replicas instantly (`--scale app=3`).

---

## 🚦 Verification, Stress Testing & Chaos Engineering

To validate the high-availability constraints under production-grade parameters, execute the following stress configurations directly on your provisioned environment.

### 1. Database Outage & Failover Resiliency (Chaos Test)

Simulate a catastrophic hardware failure on the primary write database while serving heavy read traffic.

```bash
# Gracefully terminate the primary write node
docker compose stop mysql-master

# Execute continuous queries against the endpoint
curl -I http://<your-server-ip>/api/products/1

```

* **Expected Metrics:** `GET` operations must continue resolving flawlessly with standard $\le 2\text{ms}$ response profiles if cached, or via fallback execution to `mysql-replica`. Only write mutations (`POST /admin/products/*`) should raise non-200 transaction signals during this window.

### 2. High-Concurrency Stress Profile

Execute an aggressive transaction wave using `ApacheBench (ab)` or `hey` to evaluate the load distribution performance across the application upstreams.

```bash
# Execute 5,000 requests distributed across 100 concurrent workers
ab -n 5000 -c 100 http://<your-server-ip>/api/products/1

```

* **System Observations:** Run `docker compose logs -f app` concurrently. Verify that incoming transactions are evenly divided across the distinct runtime container IDs assigned by the Nginx round-robin upstream pool. Monitor memory stability to ensure connection pooling successfully restricts socket depletion.

---

## 🚀 Step-by-Step Deployment Blueprint

### Prerequisites

* Control Node: Ansible 2.14+ installed locally.
* Managed Node: A clean Linux VPS (e.g., Hetzner CCX23 Dedicated Server running Ubuntu 22.04 LTS) with SSH key authentication configured.

### Phase 1: Local Configuration Setup

1. Clone this repository locally.
2. Navigate to `ansible/inventory.ini` and update the target configuration to reflect your environment parameters:
```ini
[production]
hetzner_server ansible_host=YOUR_SERVER_PUBLIC_IP ansible_user=root ansible_ssh_private_key_file=~/.ssh/id_ed25519

```



### Phase 2: Execution of Infrastructure Code

Trigger the playbook to handle host configuration, network isolation, database setup, and web cluster spawning in a single transaction:

```bash
cd ansible
ansible-playbook -i inventory.ini deploy.yml

```

### Phase 3: Verification

Open your target domain or public server IP address in any modern web browser:

```text
http://<YOUR_SERVER_PUBLIC_IP>/

```

The interface exposes two decoupled runtime blocks: the Customer Portal (streaming sub-millisecond cached price checks) and the Vendor Operations Portal (triggering atomic updates and automated cache cache clears).

