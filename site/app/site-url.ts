function firstHeaderValue(headers: Headers, name: string) {
  return headers.get(name)?.split(",", 1)[0]?.trim();
}

function isLocalHost(hostname: string) {
  const normalizedHostname = hostname.replace(/^\[|\]$/g, "").toLowerCase();

  return (
    normalizedHostname === "localhost" ||
    normalizedHostname === "::1" ||
    /^127(?:\.\d{1,3}){3}$/.test(normalizedHostname)
  );
}

export function siteUrlFromHeaders(input: Headers): URL {
  const directHost = input.get("host")?.trim() || "localhost";
  const directUrl = new URL(`https://${directHost}`);
  const trustsForwardedOrigin = isLocalHost(directUrl.hostname);
  const host = trustsForwardedOrigin
    ? firstHeaderValue(input, "x-forwarded-host") ?? directHost
    : directHost;
  const forwardedProtocol = trustsForwardedOrigin
    ? firstHeaderValue(input, "x-forwarded-proto")?.toLowerCase()
    : undefined;
  const protocol = forwardedProtocol === "http" || forwardedProtocol === "https" ? forwardedProtocol : "https";
  const siteUrl = new URL(`${protocol}://${host.replace(/\/+$/, "")}`);

  if (isLocalHost(siteUrl.hostname)) {
    siteUrl.protocol = "http:";
  }

  siteUrl.pathname = "/";
  return siteUrl;
}
