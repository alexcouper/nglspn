"use client";

import {
  BoldItalicUnderlineToggles,
  ConditionalContents,
  CreateLink,
  InsertCodeBlock,
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
import { useRef } from "react";
import { articleCodeMirrorExtensions } from "./article-codemirror-theme";
import { ArticleImageDialog } from "./ArticleImageDialog";
import { ImageUploadStatusBar } from "./ImageUploadStatusBar";
import { InsertImageButton } from "./InsertImageButton";
import { useImageUploadStatus } from "./useImageUploadStatus";

interface Props {
  projectRef: string;
  // Inline images are uploaded against the article, so the page creates the
  // draft before mounting the editor.
  articleId: string;
  initialMarkdown: string;
  onChange: (markdown: string) => void;
}

export function ArticleEditor({
  projectRef,
  articleId,
  initialMarkdown,
  onChange,
}: Props) {
  const editorRef = useRef<MDXEditorMethods>(null);
  const { status, uploadImage, dismissError } = useImageUploadStatus(
    projectRef,
    articleId,
  );

  return (
    <div className="rounded-lg border border-border bg-white">
      <ImageUploadStatusBar status={status} onDismissError={dismissError} />
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
          imagePlugin({
            imageUploadHandler: uploadImage,
            ImageDialog: ArticleImageDialog,
          }),
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
                        <InsertImageButton />
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
