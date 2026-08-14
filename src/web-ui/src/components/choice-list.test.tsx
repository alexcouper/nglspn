import { describe, expect, it, vi } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";

import { ChoiceList, type Choice } from "./ChoiceList";

// ------------------------------------------------------------------ mounting

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

// --------------------------------------------------------------- factories

function choice(overrides: Partial<Choice> = {}): Choice {
  return {
    id: "choice-1",
    title: "June round",
    subtitle: "Deadline June 30, 2026",
    imageUrl: "https://example.com/june.jpg",
    ...overrides,
  };
}

function radios(container: HTMLElement): HTMLInputElement[] {
  return [
    ...container.querySelectorAll('input[type="radio"]'),
  ] as HTMLInputElement[];
}

// -------------------------------------------------------------------- tests

describe("ChoiceList", () => {
  it("renders a radio per choice when there is something to choose between", async () => {
    const { container, unmount: cleanup } = await mount(
      <ChoiceList
        name="round"
        choices={[choice(), choice({ id: "choice-2", title: "Summer one-off" })]}
        selectedId="choice-2"
        onSelect={vi.fn()}
      />,
    );

    expect(radios(container)).toHaveLength(2);
    expect(radios(container)[1].checked).toBe(true);
    expect(container.textContent).toContain("June round");
    expect(container.textContent).toContain("Summer one-off");
    cleanup();
  });

  it("selecting a choice reports it", async () => {
    const onSelect = vi.fn();
    const { container, unmount: cleanup } = await mount(
      <ChoiceList
        name="round"
        choices={[choice(), choice({ id: "choice-2", title: "Summer one-off" })]}
        selectedId="choice-1"
        onSelect={onSelect}
      />,
    );

    await act(async () => {
      radios(container)[1].click();
    });

    expect(onSelect).toHaveBeenCalledWith("choice-2");
    cleanup();
  });

  it("renders a single choice without a radio, since there is nothing to choose", async () => {
    const { container, unmount: cleanup } = await mount(
      <ChoiceList
        name="round"
        choices={[choice()]}
        selectedId="choice-1"
        onSelect={vi.fn()}
      />,
    );

    expect(radios(container)).toHaveLength(0);
    expect(container.textContent).toContain("June round");
    expect(container.textContent).toContain("Deadline June 30, 2026");
    cleanup();
  });

  it("falls back to the initial where a choice has no image", async () => {
    const { container, unmount: cleanup } = await mount(
      <ChoiceList
        name="round"
        choices={[choice({ imageUrl: null })]}
        selectedId="choice-1"
        onSelect={vi.fn()}
      />,
    );

    expect(container.querySelector("img")).toBeNull();
    expect(container.textContent).toContain("J");
    cleanup();
  });

  it("renders nothing when there is nothing to offer", async () => {
    const { container, unmount: cleanup } = await mount(
      <ChoiceList
        name="round"
        choices={[]}
        selectedId={null}
        onSelect={vi.fn()}
      />,
    );

    expect(container.textContent).toBe("");
    cleanup();
  });
});
