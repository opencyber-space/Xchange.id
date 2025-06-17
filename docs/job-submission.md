# Job submission system

The Job Submission System is a dynamic, rule-driven pipeline designed to flexibly route jobs based on user intent, configuration, and context. Whether the job is targeted to a specific task DB, defined by a set of search constraints, or left without explicit preferences, the system intelligently interprets the payload, validates its structure, and determines the appropriate submission path. Jobs can be directed to a private organization task DB, routed through discovery mechanisms using metadata and rule evaluation, or pushed to a global task DB by default. This architecture ensures scalable, intent-aware job processing while maintaining support for both automated and user-driven workflows.

## Job Submission System – Architectural Flow Documentation

The **Job Submission System** is a dynamic pipeline that intelligently parses, interprets, and routes job tasks based on the user's input. It supports private, public, and rules-based task distribution modes, offering flexibility and control over where and how jobs are processed.

---

## Overview of the Flow

### 1. **User Submits a Job**

The process begins when a user or external system submits a job payload through the **Job Submission API**. This payload typically contains the job goal, requirements, constraints, and optionally, target task DB identifiers or preferences.

---

## 2. **Initial Parsing and Classification**

* The system performs **initial parsing** using a DSL interpreter to understand what the job is about.
* It passes through:

  * **Protocol DB validator** – Ensures the input structure aligns with predefined templates.
  * **Job intent identifier** – Determines the type of job and its processing intent.
  * **Intermediate payload generator** – Converts input into a uniform internal format consumable by downstream modules.

---

## 3. **Decision Phase: Routing the Job**

Based on the parsed content, the system branches into one of the following paths:

---

### A. **Job Specifies a Task DB ID Explicitly**

* If the payload includes a `task_db_id`, the system bypasses discovery.
* The job is **submitted directly** to the corresponding Task DB using the resolved service URL.
* This mode is used when the sender knows where the job must go (e.g., private org DB).

---

### B. **Job Includes Job Requirements (but no DB ID)**

* If the job includes **semantic requirements or constraints** but no DB ID:

  * The system invokes the **Job Registry Search API** to filter task DBs matching the provided query.
  * A **rule executor** evaluates results using internal DSL-based rules.
  * The **most appropriate Task DB** is selected.
  * The job is then **routed and submitted** to the selected DB.

---

### C. **No Requirements or Preferences Provided**

* If neither `task_db_id` nor search constraints are provided:

  * The job is routed to a **default global Task DB** using the **Global Tasks DB Pusher**.
  * This ensures the job is still posted and discoverable even without any custom routing logic.

---

### D. **Private Direct Push Mode**

* For certain internal org-level submissions:

  * The job can be pushed directly to a **private Task DB channel** belonging to the organization.
  * This bypasses public/global registries and acts as a fast-track posting path.

---

## 4. **Final Submission and Execution**

* Once routed, the **Job Submission Client API** handles the actual transmission to the resolved Task DB.
* Jobs submitted are now visible to **agents, executors, or auction systems** based on the target DB's access policy.
* The **Action Executor** handles immediate post-submission actions (e.g., triggering pipelines, workflows, or verification).

---

## Summary of Routing Logic

| Input Condition             | Routing Decision                     |
| --------------------------- | ------------------------------------ |
| `task_db_id` provided       | Submit directly to specified Task DB |
| Job requirements provided   | Run query → select DB → submit       |
| No requirements or ID       | Submit to Global Task DB             |
| Special internal submission | Push to private channel Task DB      |


---

## Job Submission APIs

These APIs handle job intake workflows including validation, schema mapping, and final submission with routing logic. This system ensures consistent job structure and dynamic dispatching based on assignment data.

---

### POST `/job-submission/validate`

**Description:**
Validates the job submission input by mapping it to internal schema format and performing field-level checks.

**Request Body Example:**

```json
{
  "jobId": "job-001",
  "jobGoal": { "type": "summarization" },
  "jobObjectives": ["analyze", "summarize"],
  "jobPriorityValue": 5,
  "jobCompletionMode": "single_window",
  "submittedBy": "org-123",
  "jobOutputTemplateId": "template-xyz",
  "jobVerificationSubjectIds": ["agent-456"]
}
```

**Validation Performed:**

* Required fields must be present and of correct type.
* Enumerated fields (e.g. `jobCompletionMode`) are checked against allowed values.
* All flexible fields (e.g., `job_goal`, `job_sla_terms_json`) are type-validated if present.

**Success Response:**

```json
{
  "success": true,
  "data": {
    "job_id": "job-001",
    "job_goal": { "type": "summarization" },
    ...
  },
  "message": "Validation passed"
}
```

**Failure Response:**

```json
{
  "success": false,
  "message": "job_objectives must be a list or None"
}
```

---

### POST `/job-submission/map`

**Description:**
Maps a user-facing job submission format to internal database schema format without validating it.

**Request Body:**
Same structure as `/validate`.

**Response:**

```json
{
  "success": true,
  "data": {
    "job_id": "job-001",
    "job_goal": { ... },
    ...
  },
  "message": "Mapping completed"
}
```

**Use Case:**
Useful for client-side previews, data transformation checks, or schema-aligned logging.

---

### POST `/job-submission/submit`

**Description:**
Handles full job submission lifecycle:

* Validates input
* Maps to internal DB format
* Generates a `job_id` (UUID)
* Runs assignment logic to determine target task DB
* Returns the selected task DB and assigned job ID

**Request Body Example:**

```json
{
  "jobData": {
    "jobGoal": { "type": "summarization" },
    "jobObjectives": ["analyze"],
    "jobPriorityValue": 10,
    "jobCompletionMode": "multi_window",
    "submittedBy": "org-789",
    "jobOutputTemplateId": "template-abc",
    "jobVerificationSubjectIds": ["agent-001"]
  },
  "assignmentInfo": {
    "clusterPreference": "cluster-east",
    "region": "us-east"
  }
}
```

**Success Response:**

```json
{
  "success": true,
  "data": {
    "job_id": "a6c4d4f2-b2ab-4f11-a497-0c18aa8fbabc",
    "task_db_id": "taskdb-245"
  },
  "message": "Job submitted successfully"
}
```

**Failure Response:**

```json
{
  "success": false,
  "message": "job_output_template_id must be a string"
}
```

---

## TaskDB registry search and TaskDB tasks search APIs

These endpoints enable two distinct types of search operations:

1. **Search for a Task DB** from the **Task DB Registry** based on metadata (e.g., tags, cluster ID, associated collections).
2. **Search for Jobs (Tasks)** inside a specific **Task DB** — each job follows the job schema.

---

### 1. POST `/search/task_registries`

**Purpose:**
Searches the **Task DB Registry** to locate **Task DBs** that match specified metadata filters.

**Used For:**
Finding which Task DB(s) in the network are suitable for a particular category of tasks (e.g., by domain, cluster, tags).

---

**Request Body Example:**

```json
{
  "task_registry_id": "task-registry-001",
  "query": {
    "search_metadata.tags": { "$in": ["vision", "segmentation"] },
    "accessibility_data.visibility": "public"
  }
}
```

**Parameters:**

| Field              | Type     | Required | Description                                                 |
| ------------------ | -------- | -------- | ----------------------------------------------------------- |
| `task_registry_id` | `string` | Yes      | ID used to fetch the Task DB registry's endpoint.           |
| `query`            | `object` | Yes      | Mongo-style filter used to find Task DBs from the registry. |

**Backend Flow:**

* Resolves registry metadata via `task_registry_id`.
* Uses `TasksDBRegistryClient` to query the Task DB registry with `query_tasks()`.

**Success Response:**

```json
{
  "success": true,
  "data": [
    {
      "task_listing_db_id": "taskdb-567",
      "task_db_cluster_id": "cluster-west",
      "search_metadata": {
        "tags": ["vision", "segmentation"]
      }
    }
  ],
  "message": "Matching Task DBs retrieved successfully"
}
```

---

### 2. POST `/search/task_registry`

**Purpose:**
Searches for **submitted jobs** within a specific **Task DB**, where each job follows the `JobCoreData` schema.

**Used For:**
Querying actual jobs/tasks inside a selected Task DB (e.g., open jobs, jobs by priority, submitted by org X).

---

**Request Body Example:**

```json
{
  "task_registry_id": "task-registry-001",
  "query": {
    "job_goal.type": "translation",
    "job_priority_value": { "$gte": 7 },
    "submitted_by": "org-123"
  }
}
```

**Parameters:**

| Field              | Type     | Required | Description                                             |
| ------------------ | -------- | -------- | ------------------------------------------------------- |
| `task_registry_id` | `string` | Yes      | Used to resolve the corresponding Task DB's API URL.    |
| `query`            | `object` | Yes      | Mongo-style filter applied to the `JobCoreData` schema. |

**Example Query Fields (from `JobCoreData`):**

* `job_goal.type`
* `job_completion_mode`
* `job_priority_value`
* `submitted_by`
* `job_verification_subject_ids`
* `job_output_template_id`

**Backend Flow:**

* Resolves the Task DB metadata via `task_registry_id`.
* Uses `TasksRegistryClient` to send `.query_jobs()` with translated query.

**Success Response:**

```json
{
  "success": true,
  "data": [
    {
      "job_id": "job-001",
      "job_goal": { "type": "translation" },
      "submitted_by": "org-123",
      "job_priority_value": 8,
      "job_completion_mode": "single_window"
    },
    ...
  ],
  "message": "Matching jobs retrieved successfully"
}
```

---

### Summary Table

| Endpoint                  | Description                                                    |
| ------------------------- | -------------------------------------------------------------- |
| `/search/task_registries` | Search Task **DBs** in the registry using metadata             |
| `/search/task_registry`   | Search **Jobs** inside a specific Task DB (JobCoreData format) |

---

Here is the **enhanced documentation** for your `/search/task_registry` and `/search/task_registries` APIs, with a detailed explanation of the **query payload format**, which is interpreted using the provided `query_translator(...)` logic.

---

## Query Format (via `query_translator`)

The APIs accept a structured, declarative query format that gets **translated into a MongoDB-compatible query** using a custom `query_translator(...)`. This enables clients to express nested logical and comparison conditions without writing raw MongoDB syntax.

---

### Query Object Format

Each query can be:

* A **simple condition** (`variable`, `operator`, `value`)
* Or a **logical group** (`logicalOperator`, `conditions[]`)

---

### Supported Operators

| Operator | Description                  | MongoDB Equivalent           |
| -------- | ---------------------------- | ---------------------------- |
| `==`     | Equality                     | `{ field: value }`           |
| `IN`     | Value in list                | `{ field: { $in: [...] } }`  |
| `LIKE`   | Pattern match (wildcard `*`) | `{ field: { $regex: ... } }` |
| `<`      | Less than                    | `{ field: { $lt: value } }`  |
| `<=`     | Less than or equal           | `{ field: { $lte: value } }` |
| `>`      | Greater than                 | `{ field: { $gt: value } }`  |
| `>=`     | Greater than or equal        | `{ field: { $gte: value } }` |

---

### Logical Combinators

| Logical Operator | Description                       | MongoDB Equivalent |
| ---------------- | --------------------------------- | ------------------ |
| `AND`            | All conditions must match         | `{ $and: [...] }`  |
| `OR`             | At least one condition must match | `{ $or: [...] }`   |

---

### Example 1: Simple Query

**Input Query:**

```json
{
  "variable": "job_goal.type",
  "operator": "==",
  "value": "summarization"
}
```

**Translated MongoDB Query:**

```json
{
  "job_goal.type": "summarization"
}
```

---

### Example 2: Compound AND/OR

**Input Query:**

```json
{
  "logicalOperator": "AND",
  "conditions": [
    {
      "variable": "job_priority_value",
      "operator": ">=",
      "value": 7
    },
    {
      "logicalOperator": "OR",
      "conditions": [
        {
          "variable": "submitted_by",
          "operator": "==",
          "value": "org-123"
        },
        {
          "variable": "submitted_by",
          "operator": "==",
          "value": "org-456"
        }
      ]
    }
  ]
}
```

**Translated MongoDB Query:**

```json
{
  "$and": [
    { "job_priority_value": { "$gte": 7 } },
    {
      "$or": [
        { "submitted_by": "org-123" },
        { "submitted_by": "org-456" }
      ]
    }
  ]
}
```

---

### Example 3: Pattern Match Using `LIKE`

**Input Query:**

```json
{
  "variable": "job_goal.type",
  "operator": "LIKE",
  "value": "*translation*"
}
```

**Translated MongoDB Query:**

```json
{
  "job_goal.type": {
    "$regex": ".*translation.*"
  }
}
```

---



