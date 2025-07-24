def classFactory(iface):
    from .drape_line_plugin import DrapedLinePlugin
    return DrapedLinePlugin(iface)
