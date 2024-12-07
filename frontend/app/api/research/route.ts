import { NextResponse } from "next/server";

export async function POST(request: Request) {
  const { query, k } = await request.json();

  // Replace with your actual FastAPI backend API endpoint
  const backendUrl = "http://127.0.0.1:8000/research"; // Change as needed

  try {
    const response = await fetch(backendUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ query, k }),
    });

    if (!response.ok) {
      throw new Error("Backend API request failed");
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error in research API route:", error);
    return NextResponse.json(
      { error: "Internal Server Error" },
      { status: 500 }
    );
  }
}
