PLATFORM_OPTIONS = ["WordPress", "Shopify", "Wix", "Squarespace", "Other / Not sure"]


PLATFORM_MARKERS = {
    "WordPress": ("/wp-content/", "/wp-includes/", "/wp-json/"),
    "Shopify": ("cdn.shopify.com", "/cdn/shop/", ".myshopify.com", "shopifycloud.com"),
    "Wix": ("wixstatic.com", ".wixsite.com", "static.parastorage.com"),
    "Squarespace": ("static1.squarespace.com", "squarespace-cdn.com", ".squarespace.com"),
}


PLATFORM_HELP = {
    "WordPress": {
        "url": "https://developer.wordpress.org/advanced-administration/performance/optimization/",
        "label": "WordPress performance help",
    },
    "Shopify": {
        "url": "https://help.shopify.com/en/manual/online-store/web-performance/improving-web-performance",
        "label": "Shopify performance help",
    },
    "Wix": {
        "url": "https://support.wix.com/en/article/site-performance-best-practices",
        "label": "Wix performance help",
    },
    "Squarespace": {
        "url": "https://support.squarespace.com/hc/en-us/articles/206545657-My-site-is-loading-slowly",
        "label": "Squarespace performance help",
    },
}


PLATFORM_ACTIONS = {
    "WordPress": {
        "render_blocking": (
            "Review recently added plugins and visual effects. Remove anything you no longer use, then test the page again.",
            "Ask your theme or plugin developer which stylesheet or script is delaying the first visible content.",
        ),
        "images": (
            "Resize and compress the large image near the top of the page, then replace it in the Media Library or page editor.",
            "Ask your theme developer to confirm that the page is not loading the full-size image when a smaller version would work.",
        ),
        "server": (
            "Ask your host whether page caching is enabled, and remove plugins you no longer need.",
            "Send the server-response result to your hosting provider first; they can check caching and server limits.",
        ),
        "lcp": (
            "Check the main image, banner, or heading visible when the page opens. Simplify it and compress any large image there.",
            "Ask your theme developer to identify the LCP element and why it is loading late.",
        ),
        "cls": (
            "Check banners, popups, ads, embeds, and images that appear late. Disable the responsible plugin temporarily and test again.",
            "Ask the plugin or theme developer to reserve space for the element before it loads.",
        ),
        "javascript": (
            "Remove unused plugins and temporarily disable nonessential popups, chat, analytics, or animation tools to find the slowdown.",
            "Ask the responsible plugin or theme developer to load its scripts later or reduce the work they perform.",
        ),
    },
    "Shopify": {
        "render_blocking": (
            "Review recently added apps, app embeds, animations, and busy theme sections. Disable one at a time and retest.",
            "Ask the app provider or theme developer which script or style is delaying the first visible content.",
        ),
        "images": (
            "Replace oversized hero or product images and reduce large slideshows. Shopify already handles image delivery and compression.",
            "Ask your theme developer to verify that the hero image is requested at the right size and priority.",
        ),
        "server": (
            "Do not add another CDN or compression service. Shopify manages those; instead, review apps, theme sections, and redirects.",
            "Contact Shopify Support if the response remains slow after testing your theme and apps.",
        ),
        "lcp": (
            "Check the hero image or main banner, reduce slideshow content, and compare performance with nonessential app embeds disabled.",
            "Ask your theme developer to identify the LCP element and make it load earlier.",
        ),
        "cls": (
            "Check announcement bars, popups, app widgets, and image sections that move after the page appears. Disable one at a time and retest.",
            "Ask the app provider or theme developer to reserve space for the moving element.",
        ),
        "javascript": (
            "Remove apps you no longer use and disable nonessential app embeds, tracking tools, animations, and popups before retesting.",
            "Ask the app provider or theme developer to reduce or delay the script work identified by the audit.",
        ),
    },
    "Wix": {
        "render_blocking": (
            "Reduce animations, third-party apps, and custom code near the top of the page, then retest.",
            "Contact Wix Support or the app provider if a Wix feature or third-party app is delaying the page.",
        ),
        "images": (
            "Use the Wix editor to replace oversized images and reduce large galleries, videos, or background media near the top of the page.",
            "Contact Wix Support if an optimized image is still being delivered much larger than it appears.",
        ),
        "server": (
            "Wix manages hosting and delivery. Check Wix status, then simplify heavy page content and third-party tools before retesting.",
            "Contact Wix Support if the server response stays slow across several tests.",
        ),
        "lcp": (
            "Simplify the first screen of the page: reduce large media, animations, galleries, and third-party widgets there.",
            "Ask Wix Support or your site designer to identify why the main visible element is loading late.",
        ),
        "cls": (
            "Check animations, galleries, embeds, banners, and apps that appear or move after the page begins loading.",
            "Ask Wix Support or the app provider about the element that the audit reports as moving.",
        ),
        "javascript": (
            "Remove unused apps and third-party code, and reduce nonessential animations or widgets. Retest after each change.",
            "Contact the app provider or Wix Support if built-in or third-party scripts remain the main cause.",
        ),
    },
    "Squarespace": {
        "render_blocking": (
            "Temporarily remove custom code, third-party scripts, heavy embeds, and animations, then retest to find the cause.",
            "Ask the script provider or a Squarespace Expert to reduce or delay the resource causing the slowdown.",
        ),
        "images": (
            "Replace oversized images, keep individual images below 500 KB when practical, and reduce large galleries or videos.",
            "Ask a Squarespace Expert to check why the main image is loading late or at the wrong size.",
        ),
        "server": (
            "Squarespace manages hosting and image delivery. Check Squarespace status, then reduce heavy page content and redirects.",
            "Contact Squarespace Support if slow server responses continue across several tests.",
        ),
        "lcp": (
            "Simplify the first screen of the page by reducing large images, video, animations, and embedded content.",
            "Ask a Squarespace Expert to identify the LCP element and any custom code delaying it.",
        ),
        "cls": (
            "Check announcement bars, popups, embeds, animations, and custom code that make content move after it appears.",
            "Ask the embed provider or a Squarespace Expert to reserve space for the moving element.",
        ),
        "javascript": (
            "Remove unused custom code and third-party embeds, then retest after disabling each external tool.",
            "Ask the script provider or a Squarespace Expert to reduce or delay the JavaScript work.",
        ),
    },
}


GENERIC_ACTIONS = {
    "render_blocking": (
        "Review recently added tools, tracking, animations, and visual effects. Disable nonessential items one at a time and retest.",
        "Ask your website provider or developer which script or stylesheet is delaying the first visible content.",
    ),
    "images": (
        "Resize and compress the largest image near the top of the page, replace it in your site editor, and retest.",
        "Ask whoever maintains the site to verify that the main image loads at the right size and priority.",
    ),
    "server": (
        "Ask your website host whether caching is enabled and whether it can investigate the slow response.",
        "Send this result to your hosting provider or developer so they can check the server and redirects.",
    ),
    "lcp": (
        "Check the main image, banner, or heading visible when the page opens and simplify any heavy content there.",
        "Ask your developer to identify the LCP element and why it is loading late.",
    ),
    "cls": (
        "Look for banners, images, ads, or embeds that move after appearing. Temporarily remove likely items and retest.",
        "Ask your developer to reserve space for the element before it loads.",
    ),
    "javascript": (
        "Remove unused add-ons and disable nonessential chat, tracking, popups, or animations one at a time before retesting.",
        "Ask your developer or add-on provider to reduce or delay the script work identified by the audit.",
    ),
}


def detect_platform(audits, page_url=""):
    """Suggest a platform from URLs already captured by Lighthouse."""
    network_audit = (audits or {}).get("network-requests") or {}
    details = network_audit.get("details") or {}
    request_items = details.get("items") or []
    urls = [page_url.lower()]
    urls.extend(
        str(item.get("url", "")).lower()
        for item in request_items
        if isinstance(item, dict)
    )

    scores = {
        platform: sum(any(marker in url for marker in markers) for url in urls)
        for platform, markers in PLATFORM_MARKERS.items()
    }
    best_platform = max(scores, key=scores.get)
    return best_platform if scores[best_platform] else None


def guidance_for(platform, fix_id):
    actions = PLATFORM_ACTIONS.get(platform, {}).get(fix_id) or GENERIC_ACTIONS[fix_id]
    help_resource = PLATFORM_HELP.get(platform)
    return {
        "owner_action": actions[0],
        "help_action": actions[1],
        "resource_url": help_resource["url"] if help_resource else None,
        "resource_label": help_resource["label"] if help_resource else None,
    }
