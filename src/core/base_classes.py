"""
tailwindcss classes for the layout of the site. Used in base.html
"""

breakpoints = {
    "md": {
        "nav": "md:translate-x-0",
        "content": "md:ml-80",
        "bars": "md:hidden",
    },
    "lg": {
        "nav": "lg:translate-x-0",
        "content": "lg:ml-80",
        "bars": "lg:hidden",
    },
    "none": {
        "nav": "-translate-x-[100vw]"
    }
}