import { useEffect, useState } from "react";
import { marked } from "marked";
import { getContent } from "../api";

// Home renders exercise/content.md (part of the seam). The Markdown is authored by the
// instructor and shipped in the repo, so rendering it as HTML is safe here.
export default function Home() {
  const [html, setHtml] = useState<string>("");
  useEffect(() => {
    getContent()
      .then((c) => setHtml(marked.parse(c.markdown, { async: false }) as string))
      .catch(() => setHtml("<p>Could not load instructions.</p>"));
  }, []);
  return <div className="card prose" dangerouslySetInnerHTML={{ __html: html }} />;
}
