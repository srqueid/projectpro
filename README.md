# WorkFlow Platform

## 1. Product Vision

The WorkFlow Platform is a versatile and extensible system designed to help organizations create and manage structured work. It allows for the creation of projects and the management of tasks using different workflow models, catering to a wide range of business needs beyond software development.

### Application Examples:

-   **Development:** Manage software, bugs, and releases.
-   **HR:** Handle recruitment, onboarding, and evaluations.
-   **Marketing:** Coordinate campaigns, content creation, and ad management.
-   **Events:** Plan and execute events from start to finish.
-   **Finance:** Oversee financial processes and approvals.
-   **Legal:** Manage legal cases and documents.
-   **Construction:** Track projects, activities, and suppliers.
-   **Administrative:** Handle internal requests and processes.
-   **Operations:** Manage work orders and operational activities.

The platform is designed to be domain-agnostic, with software development being just one of many configurable domains.

## 2. Architectural Principles

The platform is structured around four main levels:

1.  **ORGANIZATION:** Represents the top-level entity, such as a company or institution.
    -   **Projects:** Contains individual projects.
    -   **Teams:** Groups of users within the organization.
    -   **Users:** Individuals who are part of the organization.
2.  **PROJECT:** A specific initiative or work context.
    -   **Workflow:** The set of stages that work items pass through.
    -   **Issue Types:** The types of work items (e.g., Task, Bug, Story).
    -   **Rules:** Business logic and automation rules.
3.  **ISSUES:** The fundamental units of work.
    -   **Task, Story, Bug:** Examples of issue types.
    -   **Subtasks:** Smaller work items related to a parent issue.

The term "Issue" is used internally as a generic concept for any work item, not just software-related tickets. This allows for flexibility in representing different types of work, such as an HR selection process or a marketing campaign.

## 3. Conceptual Model

The main entities of the platform are:

-   **Organization:** The root-level container for all other entities.
    -   **User:** An individual with access to the platform.
    -   **Team:** A group of users.
    -   **Project:** A container for work items and related settings.
        -   **Project Settings:** Configuration options for the project.
        -   **Workflow:** The defined workflow for the project.
        -   **Issue Types:** The types of work items used in the project.
        -   **Custom Fields:** Additional fields for work items.
        -   **Board:** A visual representation of the workflow.
        -   **Backlog:** A list of work items to be done.
        -   **Automation:** Rules for automating tasks.
        -   **Reports:** Data and metrics about the project.

-   **Work Items:** The individual tasks or items of work within a project.
    -   **Epic, Story, Task, Bug, Request, Approval, Subtask:** These are examples of work item types, but they are not mandatory. Projects can define their own types.

## 4. Key Features

### Multi-Organization Support

A user can be a member of multiple organizations, making the platform suitable for SaaS (Software as a Service) offerings.

### Users and Teams

-   **User Entity:** Contains basic user information, including `id`, `name`, `email`, and `status`.
-   **Teams:** Organizations can create teams to group users. A user can belong to multiple teams.

### Roles and Permissions

The platform uses Role-Based Access Control (RBAC) with granular permissions. Roles can be defined at both the organization and project levels, and permissions can be customized.

-   **Organization Roles:** Owner, Admin, Member.
-   **Project Roles:** Admin, Manager, Contributor, Viewer.

### Project Templates

To streamline project creation, the platform will offer project templates for different methodologies, such as Kanban, Scrum, Marketing, and HR. Users will also be able to create their own custom templates.

### Issue Engine

The core of the platform is a flexible "Issue Engine" that uses a generic `work_items` table with configurable `work_item_types`. This allows different projects to define their own types of work, such as "Bug" for software, "Campaign" for marketing, or "Candidate" for HR.

### Custom Fields

Projects can define custom fields for their work items, allowing them to capture domain-specific information. For example, an HR project might have fields for "Salary" and "Interview Date," while a marketing project could have fields for "Campaign" and "Budget."

### Workflow Engine

The workflow engine is also highly configurable, allowing projects to define their own statuses and transitions. Transition rules can be set up to enforce specific conditions before a work item can move from one status to another.

### Automation

The platform will support automation based on the "Event-Condition-Action" model. For example, when a work item's status changes to "Approved," an automated action could be triggered to send a notification or create a new task.

### Dependencies and Blockers

Work items can have dependencies on each other (e.g., "WorkItem A blocks WorkItem B"). The system will also allow for the tracking of blockers, providing insights into impediments.

## 5. Core Business Rules

-   **RN-001 (Identification):** Every work item must have a unique identifier within its project.
-   **RN-002 (Status):** Every work item must have a valid status from the project's workflow.
-   **RN-003 (Transition):** Work items can only change status through a permitted transition.
-   **RN-004 (Permission):** Users can only perform actions for which they have permission.
-   **RN-005 (Audit):** All significant changes must be logged in an audit trail.

## 6. Modular Architecture

To keep the core of the platform generic, domain-specific features will be implemented as optional modules or extensions.

-   **Core:** Work Items, Workflow, Users, Projects, Permissions, Dependencies, Automation, Notifications.
-   **Extensions:**
    -   **Software:** Git integration, Pull Requests, CI/CD.
    -   **Scrum:** Sprints, Burndown charts, Velocity.
    -   **Kanban:** WIP limits, Lead Time, Cycle Time.
    -   **Marketing:** Campaign management, Content approvals.
    -   **HR:** Candidate tracking, Interview scheduling.
This modular approach is crucial to prevent the core from becoming too software-centric.

## 7. MVP (Minimum Viable Product)

The initial version of the platform will focus on the following features:

-   **Foundation:** Organization, Users, Teams, Roles, Permissions, Projects.
-   **Work Management:**
    -   **Work Items:** Configurable types, priority, assignee, comments, attachments, and history.
    -   **Workflow:** Custom statuses, transitions, and rules.
    -   **Board:** Columns, drag-and-drop functionality, filters, and WIP limits.
    -   **Dependencies:** Support for "blocks" and "is blocked by" relationships.
-   **Automation:** Basic triggers, conditions, and actions.
-   **Dashboard:** Simple reporting on open, in-progress, completed, blocked, and overdue items.

This MVP will provide a functional work management platform that can be extended with more specialized features in the future.
