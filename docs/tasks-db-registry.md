# Tasks DB Registry

The **Tasks DB Registry** is a service that manages metadata and lifecycle operations for task databases within the network.

### Key Responsibilities

* **Registry of Task DBs**:
  Maintains a list of all available Task DBs in the network.

* **REST API Interface**:   
  Exposes APIs to perform standard operations on the Task DB entries:

  * **Search** – Find Task DBs based on query parameters.
  * **Retrieve** – Get details of a specific Task DB.
  * **Create** – Register a new Task DB in the registry.
  * **Update** – Modify metadata or configuration of an existing Task DB.
  * **Delete** – Remove a Task DB entry from the registry.

* **Cluster Deployment Support**:
  Provides APIs to **create a Task DB** on a target cluster, assuming the cluster configuration is provided.

---

## Task DB registry schema

The schema of Tasks DB registry is as follows:

```json
const TaskListingSchema = new mongoose.Schema({
    task_listing_db_id: { type: String, required: true },
    association_ids: { type: [String], required: true },
    task_listing_db_api_url: { type: String, required: true },
    search_metadata: { type: mongoose.Schema.Types.Mixed, required: true },
    task_db_characteristics_data: { type: mongoose.Schema.Types.Mixed, required: true },
    task_db_aggregate_performance_stats: { type: mongoose.Schema.Types.Mixed, required: true },
    collection_ids: { type: [String], required: true },
    accessibility_data: { type: mongoose.Schema.Types.Mixed, required: true }
});
```


### Schema Fields

| Field Name                            | Type              | Required | Description                                                                                                                |
| ------------------------------------- | ----------------- | -------- | -------------------------------------------------------------------------------------------------------------------------- |
| `task_listing_db_id`                  | `String`          | Yes      | A unique identifier for the task listing database.                                                                         |
| `association_ids`                     | `Array of String` | Yes      | List of associated identifiers (e.g., related systems, registries, or groups).                                             |
| `task_listing_db_api_url`             | `String`          | Yes      | The base URL of the REST API for this task database.                                                                       |
| `task_db_cluster_id`                  | `String`          | Yes      | Identifier of the cluster where this task database is deployed.                                                            |
| `search_metadata`                     | `Mixed` (Object)  | Yes      | Custom metadata used for indexing and searching. Can include tags, descriptions, and other search-relevant attributes.     |
| `task_db_characteristics_data`        | `Mixed` (Object)  | Yes      | Technical characteristics and capabilities of the task database, such as type, performance profile, or architecture.       |
| `task_db_aggregate_performance_stats` | `Mixed` (Object)  | Yes      | Aggregated performance metrics such as latency, throughput, or usage statistics.                                           |
| `collection_ids`                      | `Array of String` | Yes      | Identifiers of task collections this DB belongs to. Useful for grouping and retrieval.                                     |
| `accessibility_data`                  | `Mixed` (Object)  | Yes      | Access control configuration including visibility (e.g., public/private), authorization rules, and role-based permissions. |

---


## Task Listing Registry APIs

These APIs allow users to manage Task Listing entries in the system, including creating, reading, updating, deleting, and querying records associated with task databases across clusters.

### Base Path

`/task-listing`

---

### POST `/create`

**Description:**
Creates a new Task Listing entry after verifying the availability of the `task_listing_db_api_url`.

**Request Body:**

```json
{
  "task_listing_db_id": "string",
  "association_ids": ["string"],
  "task_listing_db_api_url": "string",
  "task_db_cluster_id": "string",
  "search_metadata": { },
  "task_db_characteristics_data": { },
  "task_db_aggregate_performance_stats": { },
  "collection_ids": ["string"],
  "accessibility_data": { }
}
```

**Responses:**

* `201 Created`: Task listing created successfully.
* `500 Internal Server Error`: Error during creation or health check failure.

---

### GET `/read`

**Description:**
Reads all Task Listing entries matching optional query parameters.

**Query Parameters (optional):**

* Any field in the schema can be used as a filter (e.g., `task_db_cluster_id=cluster-1`)

**Response:**

* `200 OK`: List of matching task listings.
* `500 Internal Server Error`: Failed to fetch documents.

---

### PUT `/update`

**Description:**
Updates Task Listing documents matching a given filter.

**Request Body:**

```json
{
  "filter": { "task_db_cluster_id": "cluster-1" },
  "updateData": { "search_metadata.category": "updated-category" }
}
```

**Responses:**

* `200 OK`: Update operation result.
* `500 Internal Server Error`: Error during update.

---

### DELETE `/delete`

**Description:**
Deletes all Task Listings that match the provided filter.

**Request Body:**

```json
{
  "filter": { "task_db_cluster_id": "cluster-1" }
}
```

**Responses:**

* `200 OK`: Deletion result.
* `500 Internal Server Error`: Error during deletion.

---

### GET `/getById/:task_listing_db_id`

**Description:**
Fetches a specific Task Listing by its `task_listing_db_id`.

**Path Parameter:**

* `task_listing_db_id` – ID of the Task Listing to retrieve.

**Responses:**

* `200 OK`: Document found.
* `404 Not Found`: No matching document.
* `500 Internal Server Error`: Retrieval error.

---

### POST `/query`

**Description:**
Performs advanced Mongo-style queries on the Task Listing collection.

**Request Body:**

```json
{
  "search_metadata.category": "classification",
  "accessibility_data.visibility": "public"
}
```

**Responses:**

* `201 Created`: Query results returned successfully.
* `500 Internal Server Error`: Query execution failed.

---

### Notes

* **Health Check Enforcement**:
  During creation, a health check (`GET /health`) is performed against the `task_listing_db_api_url`. If this check fails, the creation is aborted.

* **Filtering**:
  The `/read`, `/query`, and `/update` endpoints support nested filtering using MongoDB-compatible syntax.

* **Logging**:
  Each operation logs to console with context, helpful during debugging or system monitoring.

---

## Task DB Infrastructure APIs


### 1. POST `/manual-health-check`

**Description:**
Performs a manual health check by retrieving the `task_listing_db_api_url` associated with the provided `task_listing_db_id`, then performing an HTTP GET request to `<api_url>/health`.

**Request Body:**

```json
{
  "task_listing_db_id": "taskdb-001"
}
```

**Behavior:**

* Retrieves the Task Listing document by `task_listing_db_id`.
* Extracts `task_listing_db_api_url`.
* Performs a `GET` request to `<task_listing_db_api_url>/health`.

**Responses:**

* `200 OK`: Health check passed.
* `500 Internal Server Error`: Failed to connect or task listing not found.

---

### 2. POST `/create-task-db`

**Description:**
Deploys a new Task DB instance to the specified Kubernetes cluster using the provided kubeconfig, DB configuration parameters, and metadata. Also creates a corresponding Task Listing entry with the derived API URL.

**Request Body:**

```json
{
  "task_listing_db_id": "taskdb-002",
  "association_ids": ["teamX", "projectY"],
  "task_db_cluster_id": "cluster-west",
  "search_metadata": { "tags": ["ml"], "category": "classification" },
  "task_db_characteristics_data": { "engine": "MongoDB", "replication": true },
  "task_db_aggregate_performance_stats": { "initial": true },
  "collection_ids": ["collection-alpha"],
  "accessibility_data": { "visibility": "private", "auth_required": true },
  "kube_config": {
    "clusters": [...],
    "contexts": [...],
    "current-context": "...",
    "users": [...]
  },
  "db_size_gb": 10,
  "replicas": 2
}
```

**Behavior:**

* Uses the provided kubeconfig to:

  * Authenticate with the Kubernetes cluster.
  * Deploy a DB (e.g., MongoDB) with the specified size and replica count.
* Constructs the public API URL as:
  `http://<cluster-public-host-from-kubeconfig>:32555`
* Performs internal health check on the deployed DB.
* Saves the full Task Listing document to the registry.

**Responses:**

* `201 Created`: Task DB successfully deployed and registered.
* `500 Internal Server Error`: Deployment failed or validation error.

---

### 3. GET `/resolve-cluster-url`

**(Optional Utility API)**

**Description:**
Extracts and returns the public cluster hostname (used to construct API URL) from the provided `kube_config`.

**Request Body:**

```json
{
  "kube_config": {
    "clusters": [...],
    "contexts": [...],
    "current-context": "...",
    "users": [...]
  }
}
```

**Response:**

```json
{
  "cluster_public_url": "public.cluster.domain"
}
```

**Use Case:**
Useful for debugging or for clients to verify what API base URL would be used before triggering DB creation.

---

