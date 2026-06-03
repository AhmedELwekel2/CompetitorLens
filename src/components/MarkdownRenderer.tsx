"use client";

import ReactMarkdown from "react-markdown";

/**
 * Renders markdown AI-insight text into styled HTML.
 * Uses the app's Tailwind design tokens.
 */
export default function MarkdownRenderer({ content }: { content: string }) {
  if (!content) return null;

  return (
    <ReactMarkdown
      components={{
        h1: ({ children }) => (
          <h1 className="text-lg font-bold text-text-heading mt-4 mb-2">{children}</h1>
        ),
        h2: ({ children }) => (
          <h2 className="text-base font-bold text-text-heading mt-4 mb-2">{children}</h2>
        ),
        h3: ({ children }) => (
          <h3 className="text-sm font-bold text-text-heading mt-3 mb-1.5">{children}</h3>
        ),
        h4: ({ children }) => (
          <h4 className="text-[13px] font-bold text-text-heading mt-2 mb-1">{children}</h4>
        ),
        p: ({ children }) => (
          <p className="text-[13px] text-text-secondary leading-relaxed mb-2">{children}</p>
        ),
        ul: ({ children }) => (
          <ul className="list-disc ml-5 mb-2 space-y-1">{children}</ul>
        ),
        ol: ({ children }) => (
          <ol className="list-decimal ml-5 mb-2 space-y-1">{children}</ol>
        ),
        li: ({ children }) => (
          <li className="text-[13px] text-text-secondary leading-relaxed">{children}</li>
        ),
        strong: ({ children }) => (
          <strong className="font-semibold text-text-heading">{children}</strong>
        ),
        em: ({ children }) => (
          <em className="italic text-text-primary">{children}</em>
        ),
        hr: () => (
          <hr className="border-t border-border-light my-4" />
        ),
        blockquote: ({ children }) => (
          <blockquote className="border-l-3 border-primary/30 pl-4 my-3 italic text-text-secondary">
            {children}
          </blockquote>
        ),
        code: ({ className, children, ...props }) => {
          const isInline = !className;
          return isInline ? (
            <code
              className="bg-bg-main px-1.5 py-0.5 rounded text-[12px] font-mono text-primary"
              {...props}
            >
              {children}
            </code>
          ) : (
            <code
              className="block bg-bg-main p-3 rounded-lg text-[12px] font-mono text-text-secondary overflow-x-auto my-2"
              {...props}
            >
              {children}
            </code>
          );
        },
        a: ({ href, children }) => (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary hover:text-primary-hover underline"
          >
            {children}
          </a>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
}