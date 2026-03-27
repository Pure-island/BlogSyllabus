"use client";

export function ArticleTitleLink({
  title,
  url,
  className = "",
}: {
  title: string;
  url: string;
  className?: string;
}) {
  return (
    <a
      href={url}
      target="_blank"
      rel="noreferrer"
      className={`transition hover:text-sky-800 hover:underline underline-offset-4 ${className}`.trim()}
      title={title}
    >
      {title}
    </a>
  );
}
