PLATFORM_OPTIONS = ["WordPress", "Shopify", "Wix", "Squarespace", "Other / Not sure"]


PLATFORM_MARKERS = {
    "WordPress": ("/wp-content/", "/wp-includes/", "/wp-json/"),
    "Shopify": ("cdn.shopify.com", "/cdn/shop/", ".myshopify.com", "shopifycloud.com"),
    "Wix": ("wixstatic.com", ".wixsite.com", "static.parastorage.com"),
    "Squarespace": ("static1.squarespace.com", "squarespace-cdn.com", ".squarespace.com"),
}


PLATFORM_HELP = {
    "WordPress": {
        "url": "https://learn.wordpress.org/lesson/website-optimization/",
        "label": "WordPress website optimization lesson",
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


PLATFORM_FIX_HELP = {
    ("WordPress", "javascript"): {
        "url": "https://wordpress.org/documentation/article/manage-plugins/",
        "label": "Manage WordPress plugins",
    },
    ("WordPress", "images"): {
        "url": "https://learn.wordpress.org/lesson/image-optimization/",
        "label": "WordPress image optimization lesson",
    },
    ("Shopify", "javascript"): {
        "url": "https://help.shopify.com/en/manual/online-store/themes/customizing-themes/apps",
        "label": "Manage Shopify app embeds",
    },
    ("Shopify", "lcp"): {
        "url": "https://help.shopify.com/en/manual/online-store/themes/theme-structure/sections-and-blocks",
        "label": "Edit or hide Shopify theme sections",
    },
    ("Wix", "images"): {
        "url": "https://support.wix.com/en/article/site-performance-optimizing-your-media",
        "label": "Wix image and media help",
    },
    ("Wix", "javascript"): {
        "url": "https://support.wix.com/en/article/site-performance-removing-unused-javascript",
        "label": "Wix unused JavaScript guidance",
    },
    ("Squarespace", "images"): {
        "url": "https://support.squarespace.com/hc/en-us/articles/360022529371-Reducing-your-page-size-for-faster-loading",
        "label": "Squarespace page size and image help",
    },
    ("Squarespace", "lcp"): {
        "url": "https://support.squarespace.com/hc/en-us/articles/360022529371-Reducing-your-page-size-for-faster-loading",
        "label": "Squarespace page size and image help",
    },
}


PLATFORM_SUPPORT = {
    "WordPress": {
        "url": "https://wordpress.org/support/forums/",
        "label": "Ask the WordPress community",
        "context": "Community advice, not a repair service. For hosting problems, contact your own host; for a paid theme or plugin, use its provider's support.",
    },
    "Shopify": {
        "url": "https://help.shopify.com/en/manual/your-account/contact-shopify-support",
        "label": "Contact Shopify Support",
        "context": "Start here if you need help finding the right contact. App or custom theme changes may need their provider or your site designer.",
    },
    "Wix": {
        "url": "https://support.wix.com/en/article/contacting-wix-customer-care-for-support",
        "label": "Contact Wix Support",
        "context": "Start here for Wix features. An outside app or custom code may need its provider or your site designer.",
    },
    "Squarespace": {
        "url": "https://support.squarespace.com/hc/en-us/requests/new",
        "label": "Contact Squarespace Support",
        "context": "Start here for Squarespace features. Custom code or outside tools may need their provider or your site designer.",
    },
}


PLATFORM_ACTIONS = {
    "WordPress": {
        "render_blocking": (
            "Use the help request below to ask which files hold up the page. You do not need to edit code or turn off apps to start.",
            "Ask your WordPress site designer to check the files holding up the page and contact their provider if needed.",
        ),
        "images": (
            "Find the image listed above in your site editor and save the original. Try a copy with a smaller file size and check that it still looks clear. If you cannot find or safely replace it, use the help request below.",
            "Ask your WordPress site designer to check the size of the image visitors actually download and replace it with a suitable smaller version.",
        ),
        "server": (
            "Open your hosting account's support chat or ticket form. Ask whether it can investigate the slow first response and check page caching, which saves a ready-made version of a page.",
            "Your hosting provider is the first contact. If it finds a theme or plugin problem, ask your WordPress site designer to follow up.",
        ),
        "lcp": (
            "Reload the page and watch for the identified content appearing late. If no item was identified, run another audit or send the help request before changing images or page content.",
            "Ask your WordPress site designer to identify which main content appears late and what is delaying it.",
        ),
        "cls": (
            "Reload the page, then scroll slowly. Watch for images appearing, banners pushing content down, or text changing size. Note what moves and when; these are clues, not confirmed causes.",
            "Send those observations to your WordPress site designer or the responsible plugin's support team. Ask them to find what causes the movement and how to prevent it.",
        ),
        "javascript": (
            "In Plugins, look for a popup, chat tool, or animation you do not need. On a test copy, turn off one at a time and check whether the page responds better.",
            "Ask the plugin's support team or your WordPress site designer to reduce the work that tool makes the browser do. Unused code in one test is not proof that a plugin can be deleted.",
        ),
    },
    "Shopify": {
        "render_blocking": (
            "Use the help request below to ask which files hold up the page. You do not need to edit code or turn off apps to start.",
            "Ask your Shopify theme designer to check the files holding up the page and contact their provider if needed.",
        ),
        "images": (
            "Find the image listed above in your site editor and save the original. Try a copy with a smaller file size and check that it still looks clear. If you cannot find or safely replace it, use the help request below.",
            "Ask your Shopify theme designer to check whether visitors download a larger image than the page needs.",
        ),
        "server": (
            "Shopify manages your hosting. Repeat the test for the same page; if the first response remains slow, open Shopify Support using the link below.",
            "Ask Shopify Support to investigate the slow first response and advise whether your theme designer or an app provider needs to help.",
        ),
        "lcp": (
            "Reload the page and watch for the identified content appearing late. If no item was identified, run another audit or send the help request before changing images or page content.",
            "Ask your Shopify theme designer to identify which main content appears late and help it appear sooner.",
        ),
        "cls": (
            "Reload the page, then scroll slowly. Watch for images appearing, banners pushing content down, or text changing size. Note what moves and when; these are clues, not confirmed causes.",
            "Ask the app provider or your Shopify theme designer to find what causes the movement and how to prevent it.",
        ),
        "javascript": (
            "In a copy of your theme, open App embeds in the theme editor. Turn off one nonessential popup, chat tool, or animation and preview the result using the guide below.",
            "Ask the app provider or your Shopify theme designer to reduce the work that tool makes the browser do. Do not uninstall an app just because some code was unused in this test.",
        ),
    },
    "Wix": {
        "render_blocking": (
            "Use the help request below to ask which files hold up the page. You do not need to edit code or turn off apps to start.",
            "Ask Wix Support or your site designer to check the files holding up the page and contact their provider if needed.",
        ),
        "images": (
            "Find the image listed above in your site editor and save the original. Try a copy with a smaller file size and check that it still looks clear. If you cannot find or safely replace it, use the help request below.",
            "Ask Wix Support or your site designer to check whether visitors download an image larger than the page needs.",
        ),
        "server": (
            "Wix manages your hosting. Repeat the test for the same page; if the first response remains slow, open Wix Support using the link below.",
            "Ask Wix Support to investigate the slow first response before changing your page content.",
        ),
        "lcp": (
            "Reload the page and watch for the identified content appearing late. If no item was identified, run another audit or send the help request before changing images or page content.",
            "Ask Wix Support or your site designer to identify why the main content appears late.",
        ),
        "cls": (
            "Reload the page, then scroll slowly. Watch for images appearing, banners pushing content down, or text changing size. Note what moves and when; these are clues, not confirmed causes.",
            "Ask Wix Support, your site designer, or the app provider to find what causes the movement and how to prevent it.",
        ),
        "javascript": (
            "In the Wix editor, try turning off one nonessential animation or app feature. Use the guide below to review extra tools, and preview the page before publishing.",
            "Ask Wix Support about built-in features or the app provider about outside tools. Ask them to reduce the work that makes the page slow to respond.",
        ),
    },
    "Squarespace": {
        "render_blocking": (
            "Use the help request below to ask which files hold up the page. You do not need to edit code or turn off apps to start.",
            "Ask your Squarespace site designer or Squarespace Support to check the files holding up the page.",
        ),
        "images": (
            "Find the image listed above in your site editor and save the original. Try a copy with a smaller file size and check that it still looks clear. If you cannot find or safely replace it, use the help request below.",
            "Ask your Squarespace site designer to check why the main image downloads slowly or at a larger size than needed.",
        ),
        "server": (
            "Squarespace manages your hosting. Repeat the test for the same page; if the first response remains slow, open Squarespace Support using the link below.",
            "Ask Squarespace Support to investigate the slow first response before changing your page content.",
        ),
        "lcp": (
            "Reload the page and watch for the identified content appearing late. If no item was identified, run another audit or send the help request before changing images or page content.",
            "Ask your Squarespace site designer to identify which main content appears late and what is delaying it.",
        ),
        "cls": (
            "Reload the page, then scroll slowly. Watch for images appearing, banners pushing content down, or text changing size. Note what moves and when; these are clues, not confirmed causes.",
            "Ask your Squarespace site designer or the tool's provider to find what causes the movement and how to prevent it.",
        ),
        "javascript": (
            "In the page editor, try hiding one nonessential tool, such as a social feed or chat box, and preview the result. Ask your site designer to handle any custom code.",
            "Ask your Squarespace site designer or the tool's provider to reduce the work that makes the page slow to respond.",
        ),
    },
}


GENERIC_ACTIONS = {
    "lcp_text": (
        "Find this text in your page editor. Reload the page and note whether it appears late or changes font. Leave font or code changes to your site designer if you are unsure how to undo them.",
        "Ask your site designer to check what delays this text appearing, including fonts, page styles, and code that builds the page.",
    ),
    "render_blocking": (
        "Use the help request below to ask which files hold up the page. You do not need to edit code or turn off apps to start.",
        "Ask your site designer or website provider to find which files delay the first visible content and help them load sooner.",
    ),
    "images": (
        "Find the image listed above in your site editor and save the original. Try a copy with a smaller file size and check that it still looks clear. If you cannot find or safely replace it, use the help request below.",
        "Ask your site designer or website provider to check the size visitors actually download and supply a suitable smaller image.",
    ),
    "server": (
        "Open your website host's support chat or ticket form and ask it to investigate the slow first response. You can find the host's name on your website bill or account.",
        "Your hosting provider is the first contact. Ask it to check the server response and involve your site developer if it finds a code problem.",
    ),
    "lcp": (
        "Reload the page and watch for the identified content appearing late. If no item was identified, run another audit or send the help request before changing images or page content.",
        "Ask your site designer or website provider to identify which main content appears late and what is delaying it.",
    ),
    "cls": (
        "Reload the page, then scroll slowly. Watch for images appearing, banners pushing content down, or text changing size. Note what moves and when; these are clues, not confirmed causes.",
        "Send your observations to your site designer or website provider. Ask them to find what causes the movement and how to prevent it.",
    ),
    "javascript": (
        "In your site editor, look for a nonessential popup, chat tool, or animation. In a draft, turn off one item and preview whether the page responds better.",
        "Ask your site designer or the tool's provider to reduce the work that makes the page slow to respond. Do not delete code just because it was unused in one test.",
    ),
}


def detect_platform(audits, page_url=""):
    """Suggest a platform from URLs already captured by Lighthouse."""
    network_audit = audits.get("network-requests") if isinstance(audits, dict) else None
    details = network_audit.get("details") if isinstance(network_audit, dict) else None
    request_items = details.get("items") if isinstance(details, dict) else None
    request_items = request_items if isinstance(request_items, list) else []
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
    if fix_id == "lcp_text" and platform in PLATFORM_HELP:
        actions = (actions[0], actions[1].replace("your site designer", f"your {platform} site designer"))
    # General platform help is shown once for the whole plan, not as a task-specific guide.
    help_resource = PLATFORM_FIX_HELP.get((platform, fix_id))
    return {
        "owner_action": actions[0],
        "help_action": actions[1],
        "resource_url": help_resource["url"] if help_resource else None,
        "resource_label": help_resource["label"] if help_resource else None,
    }
