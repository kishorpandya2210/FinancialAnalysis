"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

// Define TypeScript interfaces for better type safety
interface SearchResult {
  text: string;
  metadata: Record<string, any>;
}

export default function ResearchAutomation() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]); // Initialize as empty array
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null); // For error messages

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null); // Reset error state
    setResults([]); // Clear previous results

    try {
      const response = await fetch("/api/research", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query, k: 5 }), // Include 'k' parameter
      });

      if (!response.ok) {
        throw new Error("Failed to fetch results");
      }

      const data = await response.json();

      // Ensure that 'results' exists and is an array
      if (Array.isArray(data.results)) {
        setResults(data.results);
      } else {
        throw new Error("Invalid response format");
      }
    } catch (error) {
      console.error("Error fetching results:", error);
      setError("An error occurred while fetching search results.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Research Automation</h1>
      <form onSubmit={handleSubmit} className="mb-4">
        <div className="flex gap-2">
          <Input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter your research query"
            className="flex-grow"
            required // Make the input required
          />
          <Button type="submit" disabled={isLoading}>
            {isLoading ? "Searching..." : "Submit"}
          </Button>
        </div>
      </form>

      {/* Display Error Message */}
      {error && <p className="text-red-500 mb-4">{error}</p>}

      {/* Display Results */}
      {results.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Results</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="list-disc pl-5">
              {results.map((result, index) => (
                <li key={index}>
                  <p>{result.text}</p>
                  {/* Optionally display metadata */}
                  {Object.keys(result.metadata).length > 0 && (
                    <pre className="text-sm text-gray-600">
                      {JSON.stringify(result.metadata, null, 2)}
                    </pre>
                  )}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
