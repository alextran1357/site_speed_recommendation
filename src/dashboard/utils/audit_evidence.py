"""Keep a small, validated set of item-level Lighthouse findings."""
import math
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit


def valid_number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0 else None


def usable_audit(audit):
    return isinstance(audit, dict) and not audit.get("errorMessage") and not audit.get("notApplicable") and audit.get("scoreDisplayMode") not in {"error", "notApplicable", "manual"}


def short_text(value, limit=300):
    return " ".join(value.split())[:limit] if isinstance(value, str) else ""


def resource_url(value, page_url=""):
    if not isinstance(value, str) or not value.strip() or len(value) > 4096:
        return ""
    try:
        url = urljoin(page_url if isinstance(page_url, str) else "", value.strip())
        parsed = urlsplit(url)
        if parsed.scheme in {"http", "https"} and parsed.hostname and not parsed.username and not parsed.password:
            return url
    except ValueError:
        pass
    return ""


class ElementSnippet(HTMLParser):
    def __init__(self, snippet):
        super().__init__(convert_charrefs=True)
        self.tag = ""
        self.attrs = {}
        self.text = []
        try:
            self.feed(snippet)
        except (ValueError, AssertionError):
            self.tag, self.attrs, self.text = "", {}, []

    def handle_starttag(self, tag, attrs):
        if not self.tag:
            self.tag, self.attrs = tag, dict(attrs)

    def handle_data(self, data):
        self.text.append(data)


def node_item(node, page_url=""):
    if not isinstance(node, dict) or node.get("type") != "node":
        return None
    snippet = short_text(node.get("snippet"), 1000)
    parsed = ElementSnippet(snippet)
    kind = {"img": "image", "image": "image", "video": "video"}.get(parsed.tag, "element")
    if parsed.tag in {"h1", "h2", "h3", "h4", "h5", "h6", "p", "span"} and "background" not in (parsed.attrs.get("style") or "").lower():
        kind = "text"
    selector = short_text(node.get("selector"), 500)
    label = short_text(node.get("nodeLabel")) or short_text(" ".join(parsed.text)) or short_text(parsed.attrs.get("alt")) or selector or parsed.tag
    if not label:
        return None
    return {
        "kind": kind, "label": label, "selector": selector, "snippet": snippet,
        "url": resource_url(parsed.attrs.get("src"), page_url) if kind == "image" else "",
    }


def detail_rows(details, depth=0):
    # Lists contain tables (and direct LCP nodes). Subitems are explanations, not extra savings.
    if not isinstance(details, dict) or depth > 6:
        return
    if details.get("type") == "node":
        yield {"node": details}
        return
    items = details.get("items")
    if not isinstance(items, list):
        return
    for item in items[:500]:
        if not isinstance(item, dict):
            continue
        if item.get("type") in {"table", "list", "node"}:
            yield from detail_rows(item, depth + 1)
        elif details.get("type") != "checklist":
            yield item


def extract_audit_items(audits, page_url=""):
    """Use current audits when present; an unavailable current audit must not revive old findings."""
    groups = {
        "lcp": ("lcp-breakdown-insight", "largest-contentful-paint-element"),
        "images": ("image-delivery-insight", "uses-responsive-images", "uses-optimized-images"),
        "render_blocking": ("render-blocking-insight", "render-blocking-resources"),
        "layout": ("cls-culprits-insight", "layout-shifts"),
        "unused_scripts": ("unused-javascript",),
        "script_work": ("bootup-time",),
    }
    findings = {}
    for group, ids in groups.items():
        selected = ids[:1] if ids[0] in audits else ids[1:]
        if group == "lcp" and "lcp-discovery-insight" in audits:
            selected = ("lcp-breakdown-insight", "lcp-discovery-insight")
        items = []
        for audit_id in selected:
            audit = audits.get(audit_id)
            if not usable_audit(audit):
                continue
            for row in detail_rows(audit.get("details")):
                node = node_item(row.get("node"), page_url)
                url = resource_url(row.get("url"), page_url)
                if group in {"lcp", "layout"} and not node:
                    continue
                if group not in {"lcp", "layout"} and not url:
                    continue
                item = {**(node or {"kind": "resource", "label": urlsplit(url).path.rsplit("/", 1)[-1] or urlsplit(url).hostname, "selector": "", "snippet": ""}), "audit_id": audit_id}
                item["url"] = url or item.get("url", "")
                if group in {"images", "unused_scripts"}:
                    value = valid_number(row.get("wastedBytes"))
                    if not value:
                        continue
                    item["savings_bytes"] = value
                elif group == "render_blocking":
                    value = valid_number(row.get("wastedMs"))
                    if value is not None:
                        item["duration_ms"] = value
                elif group == "script_work":
                    value = valid_number(row.get("total"))
                    if not value:
                        continue
                    item["cpu_ms"] = value
                elif group == "layout":
                    value = valid_number(row.get("score"))
                    if not value:
                        continue
                    item["shift_score"] = value
                if group == "lcp" and audit_id == "lcp-discovery-insight":
                    item["kind"] = "image"
                if group == "images":
                    item["kind"] = "image"
                items.append(item)
        # Keep distinct findings; repeated resource rows must not inflate savings.
        sort_key = {"images": "savings_bytes", "unused_scripts": "savings_bytes", "render_blocking": "duration_ms", "script_work": "cpu_ms", "layout": "shift_score"}.get(group)
        if sort_key:
            items.sort(key=lambda item: item.get(sort_key, 0), reverse=True)
        unique = {}
        for item in items:
            identity = (item.get("selector") if group in {"lcp", "layout"} else item.get("url")) or item.get("url") or item["label"]
            if identity not in unique:
                unique[identity] = item
            elif group == "lcp" and item["audit_id"] == "lcp-discovery-insight":
                unique[identity] = item
        findings[group] = list(unique.values())
    # Conflicting LCP nodes should be investigated, not silently picked as the correct one.
    if len(findings["lcp"]) > 1:
        findings["lcp"] = []
    lcp = next(iter(findings["lcp"]), None)
    if lcp:
        findings["images"].sort(key=lambda item: not same_element(lcp, item))
    return {group: items[:3] for group, items in findings.items()}


def same_element(left, right):
    return any(left.get(key) and left.get(key) == right.get(key) for key in ("selector", "url"))


def lcp_item(result):
    return next(iter(result.get("audit_items", {}).get("lcp", [])), None)


def lcp_image_finding(result):
    lcp = lcp_item(result)
    if not lcp or lcp["kind"] != "image":
        return None
    return next((item for item in result.get("audit_items", {}).get("images", []) if same_element(lcp, item)), None)
