"use client";

import {
  BoldItalicUnderlineToggles,
  ConditionalContents,
  CreateLink,
  InsertCodeBlock,
  InsertImage,
  InsertTable,
  ChangeCodeMirrorLanguage,
  ListsToggle,
  MDXEditor,
  type MDXEditorMethods,
  Separator,
  UndoRedo,
  codeBlockPlugin,
  codeMirrorPlugin,
  headingsPlugin,
  imagePlugin,
  linkDialogPlugin,
  linkPlugin,
  listsPlugin,
  markdownShortcutPlugin,
  quotePlugin,
  tablePlugin,
  thematicBreakPlugin,
  toolbarPlugin,
} from "@mdxeditor/editor";
import "@mdxeditor/editor/style.css";
import "./article-markdown.css";
import { useCallback, useRef } from "react";
import { api } from "@/lib/api";
import { articleCodeMirrorExtensions } from "./article-codemirror-theme";

interface Props {
  projectId: string;
  initialMarkdown: string;
  onChange: (markdown: string) => void;
}

// Uploads a dropped/pasted image through the existing project-image upload
// pipeline and returns the public URL MDXEditor inserts into the markdown.
async function uploadInlineImage(
  projectId: string,
  file: File,
): Promise<string> {
  const presigned = await api.myProjects.getImageUploadUrl(
    projectId,
    file.name,
    file.type,
    file.size,
    false,
  );

  await new Promise<void>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve();
      else reject(new Error(`Upload failed (${xhr.status})`));
    };
    xhr.onerror = () => reject(new Error("Upload failed"));
    xhr.open(presigned.method, presigned.upload_url);
    Object.entries(presigned.headers).forEach(([k, v]) =>
      xhr.setRequestHeader(k, v),
    );
    xhr.send(file);
  });

  const completed = await api.myProjects.completeImageUpload(
    projectId,
    presigned.image_id,
  );
  return completed.url;
}

export function ArticleEditor({
  projectId,
  initialMarkdown,
  onChange,
}: Props) {
  const editorRef = useRef<MDXEditorMethods>(null);

  const handleImageUpload = useCallback(
    async (file: File) => {
      try {
        return await uploadInlineImage(projectId, file);
      } catch (err) {
        // MDXEditor swallows thrown errors, so keep the message visible.
        console.error("Image upload failed", err);
        throw err;
      }
    },
    [projectId],
  );

  return (
    <div className="rounded-lg border border-border bg-white">
      <MDXEditor
        ref={editorRef}
        markdown={initialMarkdown}
        onChange={onChange}
        contentEditableClassName="markdown markdown-article min-h-[60vh] px-4 py-3 outline-none"
        plugins={[
          headingsPlugin(),
          listsPlugin(),
          quotePlugin(),
          thematicBreakPlugin(),
          linkPlugin(),
          linkDialogPlugin(),
          imagePlugin({ imageUploadHandler: handleImageUpload }),
          tablePlugin(),
          codeBlockPlugin({ defaultCodeBlockLanguage: "ts" }),
          codeMirrorPlugin({
            codeBlockLanguages: {
              "": "Plain text",
              ts: "TypeScript",
              js: "JavaScript",
              tsx: "TSX",
              jsx: "JSX",
              python: "Python",
              bash: "Shell",
              css: "CSS",
              html: "HTML",
              json: "JSON",
              md: "Markdown",
              sql: "SQL",
            },
            codeMirrorExtensions: articleCodeMirrorExtensions,
          }),
          markdownShortcutPlugin(),
          toolbarPlugin({
            toolbarClassName:
              "border-b border-border bg-muted/40 rounded-t-lg",
            toolbarContents: () => (
              <ConditionalContents
                options={[
                  {
                    when: (editor) => editor?.editorType === "codeblock",
                    contents: () => <ChangeCodeMirrorLanguage />,
                  },
                  {
                    fallback: () => (
                      <>
                        <UndoRedo />
                        <Separator />
                        <BoldItalicUnderlineToggles options={["Bold", "Italic"]} />
                        <Separator />
                        <ListsToggle options={["bullet", "number"]} />
                        <Separator />
                        <CreateLink />
                        <InsertImage />
                        <Separator />
                        <InsertTable />
                        <InsertCodeBlock />
                      </>
                    ),
                  },
                ]}
              />
            ),
          }),
        ]}
      />
    </div>
  );
}
