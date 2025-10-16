# test_task_backend_interactive_dev

## About

### 1. Candidate-Facing Trial Task Description

**Project: "Sales platform" - A platform that provides the best user experience**

**Background:**
Our platform provides services around the world. To have higher conversion we trying to provide the best user experience on the platform. We need an authentication service that integrates social login options (e.g., Google, Facebook, Twitter) alongside traditional email/password login to streamline user onboarding and increase conversion rates.

**Your Task:**
Design and partially implement the authentication service.

**Core Requirements:**
1.  **API Design & Implementation:**
    *   Design and implement a RESTful API endpoints to provide authentication via email/password and social logins.
       *   Implement traditional email/password authentication with secure password hashing.
       *   Add social login integration for a few major providers (Google, Facebook, Twitter, etc.).
    *   Implement single sign-on (SSO) functionality to allow users to log in across devices seamlessly.
    *   User session management with JWT or OAuth 2.0 tokens.
    *   Basic user profile storage (e.g., name, email, profile picture from social providers).
2.  **Security Requirements:**
    *   Use secure OAuth 2.0 flows for social logins.
    *   Protect against common vulnerabilities (e.g., CSRF, XSS). Note: it could be a description of the technical solution that introduces the features or a development plan for adding required features.
3.  **Testing and development environment:**
    *   Provide integration tests for the service. At least it should cover the simple login/password flow.
    *   Tests must be executed in a separate container from the service itself.
    *   Provide automation tools (e.g. `Makefile`, `justfile`) to check and optionally prompt installation for all development and runtime dependencies on the host machine.
    *   Tests must at least cover happy cases.
3.  **Dockerization:**
    *   Provide a `Dockerfile` to containerize your application.
4.  **Design Document (Markdown):**
    *   Your overall approach and key design decisions.
    *   **Addressing the Compliance Requirement:** Specifically detail how you've addressed or plan to address the security requirements. Discuss potential challenges and your proposed solution(s).
    *   **Advanced Observability:** Outline your strategy for comprehensive production observability.
    *   Any other assumptions made.

**Deliverables:**
1.  Source code for the authentication service.
2.  `Dockerfile` for the application.
3.  The design document (e.g., `DESIGN.md`).
4.  A `README.md` file with instructions.
5.    **A short video demonstration of the authorization process using any convenient tool (e.g., Postman)**:
 * The setup should run with a database in Docker Compose.
 * The video should clearly demonstrate the result of your work and include an explanation of the process.
 * This will help us properly review your test assignment and speed up the recruitment process.

**Important Note:**
Focus on robust design and well-structured implementation, use the best practices for the authentication services. Pay close attention to all requirements, including operational and deployment considerations. State any assumptions.
