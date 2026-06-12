import { test, expect, type Page } from "@playwright/test";

// Base URL — frontend running locally
const BASE = "http://localhost:3000";
const API = "http://localhost:8000";

// ─── Helpers ──────────────────────────────────────────────────────

async function registerAndLogin(page: Page) {
  const email = `test_${Date.now()}@example.com`;
  const password = "testpass123";

  // Register via API
  await page.request.post(`${API}/api/v1/auth/register`, {
    data: { email, password, full_name: "E2E Tester" },
  });

  // Login via API
  const loginResp = await page.request.post(`${API}/api/v1/auth/login`, {
    data: { email, password },
  });
  const { access_token, refresh_token } = await loginResp.json();

  // Set tokens in localStorage
  await page.goto(`${BASE}/login`);
  await page.evaluate(
    ({ at, rt }: { at: string; rt: string }) => {
      localStorage.setItem("access_token", at);
      localStorage.setItem("refresh_token", rt);
    },
    { at: access_token, rt: refresh_token }
  );

  return { email, access_token };
}

// ─── Tests ────────────────────────────────────────────────────────

test.describe("Health & Landing", () => {
  test("backend health endpoint returns healthy", async ({ request }) => {
    const resp = await request.get(`${API}/health`);
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    expect(body.status).toBe("healthy");
  });

  test("dashboard page loads", async ({ page }) => {
    await page.goto(BASE);
    await expect(page.locator("h1")).toContainText("AgentForge");
  });

  test("login page renders form", async ({ page }) => {
    await page.goto(`${BASE}/login`);
    await expect(page.locator("input[type='email']")).toBeVisible();
    await expect(page.locator("input[type='password']")).toBeVisible();
    await expect(page.locator("button[type='submit']")).toBeVisible();
  });

  test("login page toggles to register", async ({ page }) => {
    await page.goto(`${BASE}/login`);
    await page.click("text=Don't have an account?");
    await expect(page.locator("input[placeholder='John Doe']")).toBeVisible();
  });
});

test.describe("Auth Flow", () => {
  test("register + login via UI", async ({ page }) => {
    await page.goto(`${BASE}/login`);

    // Switch to register
    await page.click("text=Don't have an account?");

    // Fill register form
    const email = `e2e_${Date.now()}@example.com`;
    await page.fill("input[placeholder='John Doe']", "E2E User");
    await page.fill("input[type='email']", email);
    await page.fill("input[type='password']", "testpass123");

    // Submit
    await page.click("button:has-text('Create Account')");

    // Should redirect to dashboard
    await page.waitForURL("**/");
    await expect(page.locator("h1")).toContainText("AgentForge");
  });

  test("login with wrong password shows error", async ({ page }) => {
    await page.goto(`${BASE}/login`);
    await page.fill("input[type='email']", "nobody@example.com");
    await page.fill("input[type='password']", "wrongpassword");
    await page.click("button:has-text('Sign In')");

    // Should show error
    await expect(page.locator(".text-red-600")).toBeVisible();
  });
});

test.describe("Editor", () => {
  test("editor page loads with canvas", async ({ page }) => {
    await registerAndLogin(page);
    await page.goto(`${BASE}/editor`);

    // Should have the toolbar and canvas
    await expect(page.locator("text=Add Node")).toBeVisible();
    await expect(page.locator("text=Validate")).toBeVisible();
    await expect(page.locator("text=Save")).toBeVisible();
    await expect(page.locator("text=Run")).toBeVisible();
  });

  test("can add nodes from toolbar", async ({ page }) => {
    await registerAndLogin(page);
    await page.goto(`${BASE}/editor`);

    // Click Agent in toolbar
    await page.click("text=Agent");

    // A node should appear on the canvas
    await expect(page.locator(".react-flow__node")).toHaveCount(1);
  });

  test("can connect nodes with edges", async ({ page }) => {
    await registerAndLogin(page);
    await page.goto(`${BASE}/editor`);

    // Add two nodes
    await page.click("text=Input");
    await page.click("text=Agent");

    // Should have 2 nodes
    await expect(page.locator(".react-flow__node")).toHaveCount(2);
  });

  test("validate shows validation results", async ({ page }) => {
    await registerAndLogin(page);
    await page.goto(`${BASE}/editor`);

    // Click validate without any nodes
    await page.click("text=Validate");

    // Should show validation bar
    await expect(page.locator("text=Invalid")).toBeVisible();
  });

  test("workflow name is editable", async ({ page }) => {
    await registerAndLogin(page);
    await page.goto(`${BASE}/editor`);

    // Click on the workflow name
    await page.click("text=Untitled Workflow");

    // Input should appear
    await expect(page.locator("input[value='Untitled Workflow']")).toBeVisible();
  });
});

test.describe("Dashboard with Workflows", () => {
  test("shows empty state when no workflows", async ({ page }) => {
    await registerAndLogin(page);
    await page.goto(BASE);

    await expect(page.locator("text=No workflows yet")).toBeVisible();
  });

  test("New Workflow button navigates to editor", async ({ page }) => {
    await registerAndLogin(page);
    await page.goto(BASE);

    await page.click("text=New Workflow");
    await page.waitForURL("**/editor");
    await expect(page.locator("text=Add Node")).toBeVisible();
  });
});

test.describe("Navigation Pages", () => {
  test("workspace page loads", async ({ page }) => {
    await registerAndLogin(page);
    await page.goto(`${BASE}/workspaces`);
    await expect(page.locator("h1")).toContainText("Workspaces");
  });

  test("templates page loads", async ({ page }) => {
    await registerAndLogin(page);
    await page.goto(`${BASE}/templates`);
    await expect(page.locator("h1")).toContainText("Template");
  });

  test("MCP servers page loads", async ({ page }) => {
    await registerAndLogin(page);
    await page.goto(`${BASE}/mcp-servers`);
    await expect(page.locator("h1")).toContainText("MCP");
  });

  test("cost dashboard page loads", async ({ page }) => {
    await registerAndLogin(page);
    await page.goto(`${BASE}/cost`);
    await expect(page.locator("h1")).toContainText("Cost");
  });

  test("execution history page loads", async ({ page }) => {
    await registerAndLogin(page);
    await page.goto(`${BASE}/executions`);
    await expect(page.locator("h1")).toContainText("Execution");
  });
});

test.describe("API Integration", () => {
  test("workflow CRUD via API", async ({ request }) => {
    // Register
    const regResp = await request.post(`${API}/api/v1/auth/register`, {
      data: { email: `api_${Date.now()}@test.com`, password: "pass123", full_name: "API Test" },
    });
    expect(regResp.ok()).toBeTruthy();

    // Login
    const loginResp = await request.post(`${API}/api/v1/auth/login`, {
      data: { email: regResp.url().includes("test.com") ? `api_${Date.now()}@test.com` : "api_test@test.com", password: "pass123" },
    });

    // We need the token from register — use the login we just did
    const loginData = await loginResp.json();
    const token = loginData.access_token;
    const headers = { Authorization: `Bearer ${token}` };

    // Create workflow
    const createResp = await request.post(`${API}/api/v1/workflows`, {
      headers,
      data: { workspace_id: "test", name: "E2E Test Workflow", dag_json: { nodes: [], edges: [] } },
    });
    expect(createResp.ok()).toBeTruthy();
    const wf = await createResp.json();
    expect(wf.name).toBe("E2E Test Workflow");

    // List workflows
    const listResp = await request.get(`${API}/api/v1/workflows`, { headers });
    expect(listResp.ok()).toBeTruthy();

    // Validate workflow
    const valResp = await request.post(`${API}/api/v1/workflows/${wf.id}/validate`, { headers });
    expect(valResp.ok()).toBeTruthy();

    // Delete workflow
    const delResp = await request.delete(`${API}/api/v1/workflows/${wf.id}`, { headers });
    expect(delResp.ok()).toBeTruthy();
  });
});
