import ReactMarkdown from 'react-markdown';

interface MarkdownProps {
  children: string;
  /** 'light' = dark text on light bg (report panel); 'dark' = white text on dark bg (chat). */
  tone?: 'light' | 'dark';
}

/**
 * Styled markdown renderer (no typography plugin in this project, so element
 * styles are mapped explicitly to Tailwind classes).
 */
export default function Markdown({ children, tone = 'dark' }: MarkdownProps) {
  const base = tone === 'dark' ? 'text-white/90' : 'text-gray-800';
  const heading = tone === 'dark' ? 'text-white' : 'text-cgiar-dark';
  const muted = tone === 'dark' ? 'text-white/60' : 'text-gray-500';
  const link = tone === 'dark' ? 'text-cgiar-accent hover:text-green-300' : 'text-cgiar-green hover:text-cgiar-accent';
  const code = tone === 'dark' ? 'bg-white/10 text-green-200' : 'bg-gray-100 text-cgiar-dark';

  return (
    <div className={`text-sm leading-relaxed ${base}`}>
      <ReactMarkdown
        components={{
          h1: ({ children }) => <h1 className={`text-xl font-bold mt-3 mb-2 ${heading}`}>{children}</h1>,
          h2: ({ children }) => <h2 className={`text-lg font-semibold mt-3 mb-1.5 ${heading}`}>{children}</h2>,
          h3: ({ children }) => <h3 className={`text-base font-semibold mt-2 mb-1 ${heading}`}>{children}</h3>,
          p: ({ children }) => <p className="my-1.5">{children}</p>,
          ul: ({ children }) => <ul className="list-disc pl-5 my-1.5 space-y-0.5">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal pl-5 my-1.5 space-y-0.5">{children}</ol>,
          li: ({ children }) => <li>{children}</li>,
          strong: ({ children }) => <strong className={`font-semibold ${heading}`}>{children}</strong>,
          em: ({ children }) => <em className={muted}>{children}</em>,
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noopener noreferrer" className={`underline ${link}`}>
              {children}
            </a>
          ),
          code: ({ children }) => (
            <code className={`px-1 py-0.5 rounded text-xs font-mono ${code}`}>{children}</code>
          ),
          pre: ({ children }) => (
            <pre className={`p-2 rounded-md overflow-x-auto text-xs my-2 ${code}`}>{children}</pre>
          ),
          blockquote: ({ children }) => (
            <blockquote className={`border-l-2 border-cgiar-accent pl-3 my-2 ${muted}`}>{children}</blockquote>
          ),
          hr: () => <hr className={tone === 'dark' ? 'border-white/20 my-3' : 'border-gray-200 my-3'} />,
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
