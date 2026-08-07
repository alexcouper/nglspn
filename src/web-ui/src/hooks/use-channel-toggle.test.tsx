import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, useState } from "react";
import { createRoot, type Root } from "react-dom/client";
import type { ChannelFollowState, FollowState } from "@/lib/api/follows";
import { ChannelToggleList } from "@/components/ChannelToggleList";
import { ToastsProvider } from "@/contexts/toasts";
import { useChannelToggle } from "./useChannelToggle";

vi.mock("@/lib/api", () => ({
  api: {
    follows: {
      followChannel: vi.fn(),
      unfollowChannel: vi.fn(),
    },
  },
}));

// Imported after the mock so these are the mocked functions.
const { api } = await import("@/lib/api");
const followChannel = vi.mocked(api.follows.followChannel);
const unfollowChannel = vi.mocked(api.follows.unfollowChannel);

// ------------------------------------------------------------------ mounting

async function mount(element: React.ReactElement) {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  await act(async () => {
    root.render(<ToastsProvider>{element}</ToastsProvider>);
  });
  return { container, unmount: () => unmount(root, container) };
}

function unmount(root: Root, container: HTMLElement) {
  act(() => root.unmount());
  container.remove();
}

// --------------------------------------------------------------- factories

function channel(overrides: Partial<ChannelFollowState> = {}): ChannelFollowState {
  return {
    channel_id: "channel-1",
    channel_name: "Updates",
    followed: true,
    ...overrides,
  };
}

function stillFollowing(): FollowState {
  return { is_followed: true, created_at: "2026-08-01T10:00:00Z" };
}

function noLongerFollowing(): FollowState {
  return { is_followed: false, created_at: null };
}

/** A promise plus the handle to settle it, for holding a call in flight. */
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function Harness({
  channels: initial,
  onProjectUnfollowed = () => {},
}: {
  channels: ChannelFollowState[];
  onProjectUnfollowed?: () => void;
}) {
  const [channels, setChannels] = useState(initial);
  const toggle = useChannelToggle({
    projectSlug: "alpha",
    setChannels,
    onProjectUnfollowed,
  });
  return <ChannelToggleList channels={channels} onToggle={toggle} />;
}

// ----------------------------------------------------------------- helpers

function checkboxes(container: HTMLElement): HTMLInputElement[] {
  return Array.from(container.querySelectorAll("input[type=checkbox]"));
}

async function click(box: HTMLInputElement) {
  await act(async () => {
    box.click();
  });
}

function checkedStates(container: HTMLElement): boolean[] {
  return checkboxes(container).map((box) => box.checked);
}

// --------------------------------------------------------------- the tests

describe("useChannelToggle", () => {
  beforeEach(() => {
    followChannel.mockReset();
    unfollowChannel.mockReset();
    followChannel.mockResolvedValue(channel());
    unfollowChannel.mockResolvedValue(stillFollowing());
  });

  it("unchecks a followed channel and calls unfollowChannel", async () => {
    const { container, unmount: cleanup } = await mount(
      <Harness channels={[channel()]} />,
    );

    await click(checkboxes(container)[0]);

    expect(unfollowChannel).toHaveBeenCalledWith("alpha", "channel-1");
    expect(checkedStates(container)).toEqual([false]);
    cleanup();
  });

  it("checks an unfollowed channel and calls followChannel", async () => {
    const { container, unmount: cleanup } = await mount(
      <Harness channels={[channel({ followed: false })]} />,
    );

    await click(checkboxes(container)[0]);

    expect(followChannel).toHaveBeenCalledWith("alpha", "channel-1");
    expect(checkedStates(container)).toEqual([true]);
    cleanup();
  });

  it("reports the project unfollowed when the last channel goes", async () => {
    const onProjectUnfollowed = vi.fn();
    unfollowChannel.mockResolvedValue(noLongerFollowing());
    const { container, unmount: cleanup } = await mount(
      <Harness channels={[channel()]} onProjectUnfollowed={onProjectUnfollowed} />,
    );

    await click(checkboxes(container)[0]);

    expect(onProjectUnfollowed).toHaveBeenCalledTimes(1);
    cleanup();
  });

  it("leaves the project alone while other channels stay followed", async () => {
    const onProjectUnfollowed = vi.fn();
    const { container, unmount: cleanup } = await mount(
      <Harness
        channels={[channel(), channel({ channel_id: "channel-2" })]}
        onProjectUnfollowed={onProjectUnfollowed}
      />,
    );

    await click(checkboxes(container)[0]);

    expect(onProjectUnfollowed).not.toHaveBeenCalled();
    cleanup();
  });

  it("keeps both changes when two channels are toggled before either settles", async () => {
    const first = deferred<FollowState>();
    const second = deferred<FollowState>();
    unfollowChannel
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);
    const { container, unmount: cleanup } = await mount(
      <Harness channels={[channel(), channel({ channel_id: "channel-2" })]} />,
    );

    // Both clicks land against the same render, so neither handler can see
    // the other's optimistic write.
    await act(async () => {
      const boxes = checkboxes(container);
      boxes[0].click();
      boxes[1].click();
    });
    await act(async () => {
      first.resolve(stillFollowing());
      second.resolve(stillFollowing());
    });

    expect(checkedStates(container)).toEqual([false, false]);
    cleanup();
  });

  it("rolls back only the failed channel", async () => {
    const failing = deferred<FollowState>();
    unfollowChannel
      .mockReturnValueOnce(failing.promise)
      .mockReturnValueOnce(Promise.resolve(stillFollowing()));
    const { container, unmount: cleanup } = await mount(
      <Harness channels={[channel(), channel({ channel_id: "channel-2" })]} />,
    );

    await click(checkboxes(container)[0]);
    await click(checkboxes(container)[1]);
    await act(async () => {
      failing.reject(new Error("boom"));
    });

    expect(checkedStates(container)).toEqual([true, false]);
    cleanup();
  });
});
