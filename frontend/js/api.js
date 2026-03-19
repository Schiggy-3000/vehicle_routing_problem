import { BACKEND_URL } from "./config.js";

export async function fetchDistanceMatrix(addresses) {
  const res = await fetch(`${BACKEND_URL}/distance-matrix`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ addresses }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Distance matrix request failed");
  }
  return res.json(); // { matrix, duration_matrix }
}

export async function solve(payload) {
  const res = await fetch(`${BACKEND_URL}/solve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Solve request failed");
  }
  return res.json(); // SolveResponse
}
