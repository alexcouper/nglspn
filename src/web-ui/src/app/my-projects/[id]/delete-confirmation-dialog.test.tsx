import { describe, expect, it, vi } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";

import { messages } from "@/i18n/messages";
import {
  DeleteConfirmationDialog,
  matchesConfirmWord,
} from "./DeleteConfirmationDialog";

// The word the dialog asks for is copy, not a constant, so the test reads it
// from the messages. The point of these cases is that the guard keeps matching
// however that word is written.
const CONFIRM_WORD = messages["my-projects"].deleteDialog.confirmWord;

async function mount(element: React.ReactElement) {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  await act(async () => {
    root.render(element);
  });
  return { container, root, unmount: () => unmount(root, container) };
}

function unmount(root: Root, container: HTMLElement) {
  act(() => root.unmount());
  container.remove();
}

async function openDialog(onConfirm = vi.fn()) {
  const { container, unmount } = await mount(
    <DeleteConfirmationDialog
      isOpen
      projectTitle="Hornsteinn"
      onConfirm={onConfirm}
      onCancel={vi.fn()}
    />,
  );
  return { container, unmount, onConfirm };
}

function confirmInput(container: HTMLElement): HTMLInputElement {
  return container.querySelector("input") as HTMLInputElement;
}

function deleteButton(container: HTMLElement): HTMLButtonElement {
  const buttons = [...container.querySelectorAll("button")];
  return buttons[buttons.length - 1] as HTMLButtonElement;
}

async function type(container: HTMLElement, text: string) {
  const input = confirmInput(container);
  const setValue = Object.getOwnPropertyDescriptor(
    HTMLInputElement.prototype,
    "value",
  )!.set!;
  await act(async () => {
    setValue.call(input, text);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

async function clickDelete(container: HTMLElement) {
  await act(async () => {
    deleteButton(container).click();
  });
}

describe("the delete confirmation dialog", () => {
  it("keeps delete disabled until the confirmation word is typed", async () => {
    const { container, unmount } = await openDialog();

    expect(deleteButton(container).disabled).toBe(true);

    await type(container, CONFIRM_WORD);

    expect(deleteButton(container).disabled).toBe(false);
    unmount();
  });

  it("accepts the confirmation word whatever case it is typed in", async () => {
    const { container, unmount } = await openDialog();

    await type(container, CONFIRM_WORD.toUpperCase());

    expect(deleteButton(container).disabled).toBe(false);
    unmount();
  });

  it("accepts the confirmation word with surrounding whitespace", async () => {
    const { container, unmount } = await openDialog();

    await type(container, `  ${CONFIRM_WORD}  `);

    expect(deleteButton(container).disabled).toBe(false);
    unmount();
  });

  it("rejects a word that is not the confirmation word", async () => {
    const { container, unmount } = await openDialog();

    await type(container, `${CONFIRM_WORD}s`);

    expect(deleteButton(container).disabled).toBe(true);
    unmount();
  });

  it("confirms the deletion once the word matches", async () => {
    const { container, unmount, onConfirm } = await openDialog();

    await type(container, CONFIRM_WORD);
    await clickDelete(container);

    expect(onConfirm).toHaveBeenCalledOnce();
    unmount();
  });
});

// The word arrives from the messages, so the comparison has to survive being
// translated. These cases are the ones a mounted test cannot reach: the shim
// renders the real English messages, so the asked-for word is always "delete".
describe("matching the typed text against the asked-for word", () => {
  it("matches the English word as it is written", () => {
    expect(matchesConfirmWord("delete", "delete")).toBe(true);
  });

  it("matches a word the translation capitalises", () => {
    expect(matchesConfirmWord("eyða", "Eyða")).toBe(true);
    expect(matchesConfirmWord("Eyða", "Eyða")).toBe(true);
    expect(matchesConfirmWord("EYÐA", "Eyða")).toBe(true);
  });

  it("matches a translated word with accents intact", () => {
    expect(matchesConfirmWord("EYÐA", "eyða")).toBe(true);
    expect(matchesConfirmWord("eyda", "eyða")).toBe(false);
  });

  it("ignores whitespace around what was typed", () => {
    expect(matchesConfirmWord("  Eyða\t", "eyða")).toBe(true);
  });

  it("does not match a different word", () => {
    expect(matchesConfirmWord("deletes", "delete")).toBe(false);
    expect(matchesConfirmWord("", "delete")).toBe(false);
  });
});
