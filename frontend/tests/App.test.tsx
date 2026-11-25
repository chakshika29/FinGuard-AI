import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { LoginPage } from "../src/components/LoginPage";
import { AuthProvider } from "../src/context/AuthContext";
import { KpiCard, riskVariant } from "../src/components/UI";

describe("FinGuard AI Frontend Components", () => {
  it("renders LoginPage with quick-fill demo role options and synthetic disclaimer", () => {
    render(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    );
    expect(screen.getByText(/FinGuard AI/i)).toBeInTheDocument();
    expect(screen.getByText(/Administrator/i)).toBeInTheDocument();
    expect(screen.getByText(/Data Steward/i)).toBeInTheDocument();
    expect(screen.getByText(/Risk Analyst/i)).toBeInTheDocument();
    expect(screen.getByText(/100% synthetic/i)).toBeInTheDocument();
  });

  it("renders KpiCard and computes riskVariant correctly", () => {
    render(<KpiCard title="Quality Score" value="97.38%" icon={<span>OK</span>} />);
    expect(screen.getByText("Quality Score")).toBeInTheDocument();
    expect(screen.getByText("97.38%")).toBeInTheDocument();
    expect(riskVariant("Critical Risk")).toBe("red");
    expect(riskVariant("High Risk")).toBe("amber");
    expect(riskVariant("Medium Risk")).toBe("blue");
    expect(riskVariant("Low Risk")).toBe("green");
  });
});
