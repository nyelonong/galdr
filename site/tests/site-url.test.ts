import { describe, expect, it, vi } from "vitest";
import { siteUrlFromHeaders } from "../app/site-url";

const headersMock = vi.hoisted(() => vi.fn());

vi.mock("next/headers", () => ({ headers: headersMock }));

describe("site URL", () => {
  it("site_url_prefers_forwarded_https_host", () => {
    const siteUrl = siteUrlFromHeaders(
      new Headers({
        host: "localhost:3000",
        "x-forwarded-host": "galdr.example.com, proxy.internal",
        "x-forwarded-proto": "https, http",
      }),
    );

    expect(siteUrl.toString()).toBe("https://galdr.example.com/");
  });

  it("site_url_uses_ordinary_host_when_not_forwarded", () => {
    const siteUrl = siteUrlFromHeaders(new Headers({ host: "preview.example.com" }));

    expect(siteUrl.toString()).toBe("https://preview.example.com/");
  });

  it("site_url_rejects_forwarded_origin_on_public_request", () => {
    const siteUrl = siteUrlFromHeaders(
      new Headers({
        host: "galdr.example.com",
        "x-forwarded-host": "attacker.invalid",
        "x-forwarded-proto": "http",
      }),
    );

    expect(siteUrl.toString()).toBe("https://galdr.example.com/");
  });

  it("site_url_keeps_localhost_http", () => {
    expect(siteUrlFromHeaders(new Headers({ host: "localhost:3000" })).toString()).toBe(
      "http://localhost:3000/",
    );
    expect(siteUrlFromHeaders(new Headers({ host: "127.0.0.1:8787" })).toString()).toBe(
      "http://127.0.0.1:8787/",
    );
  });
});

describe("dynamic metadata", () => {
  it("metadata_has_absolute_canonical_url", async () => {
    headersMock.mockResolvedValueOnce(
      new Headers({
        "x-forwarded-host": "galdr.example.com",
        "x-forwarded-proto": "https",
      }),
    );

    const { generateMetadata } = await import("../app/layout");
    const metadata = await generateMetadata();

    expect(headersMock).toHaveBeenCalledTimes(1);
    expect(metadata.alternates?.canonical).toBe("https://galdr.example.com/");
  });

  it("metadata_has_absolute_og_and_x_image_urls", async () => {
    headersMock.mockResolvedValueOnce(
      new Headers({
        "x-forwarded-host": "galdr.example.com",
        "x-forwarded-proto": "https",
      }),
    );

    const { generateMetadata } = await import("../app/layout");
    const metadata = await generateMetadata();

    expect(metadata.openGraph?.images).toEqual(["https://galdr.example.com/og.png"]);
    expect(metadata.twitter?.images).toEqual(["https://galdr.example.com/og.png"]);
  });
});
