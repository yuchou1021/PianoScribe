"""MusicXML -> 谱面图像（Verovio 排版引擎）。"""
from __future__ import annotations

from pathlib import Path


def musicxml_to_svg(xml_path: Path, out_path: Path,
                    page_width: int = 1600, page_height: int = 2200, scale: int = 60) -> str:
    """用 Verovio 把 MusicXML 渲染为 SVG（可能多页，拼接为一个文档）。

    注意：verovio 的默认字体资源路径是「模块导入线程」绑定的；在后台线程中
    直接创建 toolkit 会因字体加载失败而输出空图。因此这里使用
    initFont=False + 实例级 setResourcePath，保证任意线程都能正常渲染。
    """
    import verovio
    from importlib.resources import files

    resource_path = str(files("verovio") / "data")
    tk = verovio.toolkit(initFont=False)
    if not tk.setResourcePath(resource_path):
        raise RuntimeError("Verovio 字体资源加载失败：" + resource_path)
    tk.setOptions(
        {
            "pageWidth": page_width,
            "pageHeight": page_height,
            "scale": scale,
            "spacingStaff": 6,
            "spacingSystem": 10,
            "breaks": "auto",
            "footer": "none",
            "header": "none",
        }
    )
    if not tk.loadFile(str(xml_path)):
        raise RuntimeError("Verovio 无法解析 MusicXML 文件")
    pages = tk.getPageCount()
    if pages == 0:
        raise RuntimeError("Verovio 没有渲染出任何页面")
    try:
        svgs = [tk.renderToSVG(i + 1) for i in range(pages)]
    except Exception:
        # 渲染失败：重建 toolkit 重试一次
        tk = verovio.toolkit(initFont=False)
        tk.setResourcePath(resource_path)
        tk.setOptions(
            {
                "pageWidth": page_width,
                "pageHeight": page_height,
                "scale": scale,
                "spacingStaff": 6,
                "spacingSystem": 10,
                "breaks": "auto",
                "footer": "none",
                "header": "none",
            }
        )
        tk.loadFile(str(xml_path))
        svgs = [tk.renderToSVG(i + 1) for i in range(tk.getPageCount())]
    combined = "\n".join(svgs)
    out_path.write_text(combined, encoding="utf-8")
    return combined


def svg_to_png(svg_path: Path, png_path: Path) -> Path | None:
    """尝试把 SVG 转成 PNG（cairosvg 需系统 cairo 库，失败则返回 None）。"""
    # cairosvg
    try:
        import cairosvg

        cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), background_color="white")
        if png_path.exists() and png_path.stat().st_size > 0:
            return png_path
    except Exception:
        pass
    # svglib（纯 Python，兼容性差一些）
    try:
        from svglib.svglib import svg2rlg
        from reportlab.graphics import renderPM

        drawing = svg2rlg(str(svg_path))
        if drawing is not None:
            renderPM.drawToFile(drawing, str(png_path), fmt="PNG")
            if png_path.exists() and png_path.stat().st_size > 0:
                return png_path
    except Exception:
        pass
    return None


