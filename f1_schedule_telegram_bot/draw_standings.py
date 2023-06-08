"""
Draw driver and constructor standings and render to an image.

The `draw_standings` module contains functions to render the driver and constructor
standings on a canvas, and return a rendered image as an in memory byte buffer.
"""

import io

from PIL import Image, ImageDraw, ImageFont  # type: ignore


def draw_driver_standings(driver_standing, races):
    """Draw driver standings to a canvas; returns the rendered canvas."""
    # pylint: enable=invalid-name

    def position_text(standing):
        return f"{standing.position_text}"

    def name(standing):
        return f"{standing.driver.given_name} {standing.driver.family_name}"

    def team(standing):
        return f"{standing.constructors[0].name}"

    def points(standing):
        return f"{int(standing.points)}"

    driver_standings = driver_standing.driver_standings

    headers = ["Position", "Name", "Team", "Points"]

    col1 = max(
        [len(position_text(standing)) for standing in driver_standings]
        + [len(headers[0])]
    )
    col2 = max(
        [len(name(standing)) for standing in driver_standings] + [len(headers[1])]
    )
    col3 = max(
        [len(team(standing)) for standing in driver_standings] + [len(headers[2])]
    )
    col4 = max(
        [len(points(standing)) for standing in driver_standings] + [len(headers[3])]
    )

    title = f"Driver standing after the {races[driver_standing.round_no - 1].race_name}"

    padding = 10
    char_width = 8
    char_height = 14

    # approx. width based on content
    width = max(
        len(title * char_width) + padding * 2,
        sum(
            [
                col1 * char_width + padding,
                col2 * char_width + padding,
                col3 * char_width + padding,
                col4 * char_width + padding,
            ]
        )
        + padding,
    )
    # approx. height based on: 1 line for title text + 1 for table heading + n lines for each driver
    height = (
        padding
        + 2 * (padding + char_height)
        + len(driver_standings) * (char_height + padding)
    )

    img = Image.new("RGB", (width, height), (240, 240, 240))
    font = ImageFont.truetype("font/Rubik-Regular.ttf", 14)
    drawing = ImageDraw.Draw(img)

    # pylint: disable=invalid-name
    x1 = padding
    x2 = x1 + padding + (col1 * char_width)
    x3 = x2 + padding + (col2 * char_width)
    x4 = x3 + padding + (col3 * char_width)
    y = padding

    # title
    drawing.text((padding, y), title, font=font, fill=(188, 0, 3))
    y += padding + char_height

    # table heading
    header_fill = (120, 110, 110)
    drawing.text((x1, y), headers[0], font=font, fill=header_fill)
    drawing.text((x2, y), headers[1], font=font, fill=header_fill)
    drawing.text((x3, y), headers[2], font=font, fill=header_fill)
    drawing.text((x4, y), headers[3], font=font, fill=header_fill)

    y += padding + char_height

    for standing in driver_standings:
        drawing.text((x1, y), position_text(standing), font=font, fill=(0, 0, 0))
        drawing.text((x2, y), name(standing), font=font, fill=(0, 0, 0))
        drawing.text((x3, y), team(standing), font=font, fill=(0, 0, 0))
        drawing.text((x4, y), points(standing), font=font, fill=(0, 0, 0))

        y += padding + char_height

    # pylint: enable=invalid-name

    with io.BytesIO() as output:
        img.save(output, format="PNG")
        return output.getvalue()

    raise EncodingError("Unable to encode and write driver standings image")


def draw_constructor_standings(constructor_standing, races):
    """Draw constructor standings to a canvas; returns the rendered canvas."""
    # pylint: disable=invalid-name

    def position_text(standing):
        return f"{standing.position_text}"

    def constructor(standing):
        return f"{standing.constructor.name}"

    def points(standing):
        return f"{int(standing.points)}"

    def wins(standing, round_no):
        return f"{standing.wins} / {round_no}"

    constructor_standings = constructor_standing.constructor_standings
    round_no = constructor_standing.round_no

    headers = ["Position", "Team", "Points", "Wins"]

    col1 = max(
        [len(position_text(standing)) for standing in constructor_standings]
        + [len(headers[0])]
    )
    col2 = max(
        [len(constructor(standing)) for standing in constructor_standings]
        + [len(headers[1])]
    )
    col3 = max(
        [len(points(standing)) for standing in constructor_standings]
        + [len(headers[2])]
    )
    col4 = max(
        [len(wins(standing, round_no)) for standing in constructor_standings]
        + [len(headers[3])]
    )

    title = f"Constructor standing after the {races[round_no - 1].race_name}"

    padding = 10
    char_width = 8
    char_height = 14

    # approx. width based on content
    width = max(
        len(title * char_width) + padding * 2,
        sum(
            [
                col1 * char_width + padding,
                col2 * char_width + padding,
                col3 * char_width + padding,
                col4 * char_width + padding,
            ]
        )
        + padding,
    )
    # approx. height based on: 1 line for title text + 1 for table heading + n lines for each team
    height = (
        padding
        + (2 * (char_height + padding))
        + (len(constructor_standings) * (char_height + padding))
    )

    img = Image.new("RGB", (width, height), (240, 240, 240))
    font = ImageFont.truetype("font/Rubik-Regular.ttf", 14)
    drawing = ImageDraw.Draw(img)

    x1 = padding
    x2 = x1 + padding + (col1 * char_width)
    x3 = x2 + padding + (col2 * char_width)
    x4 = x3 + padding + (col3 * char_width)
    y = padding

    # title
    drawing.text((padding, y), title, font=font, fill=(188, 0, 3))
    y += padding + char_height

    # table heading
    header_fill = (120, 110, 110)
    drawing.text((x1, y), headers[0], font=font, fill=header_fill)
    drawing.text((x2, y), headers[1], font=font, fill=header_fill)
    drawing.text((x3, y), headers[2], font=font, fill=header_fill)
    drawing.text((x4, y), headers[3], font=font, fill=header_fill)

    y += padding + char_height

    for standing in constructor_standings:
        drawing.text((x1, y), f"{position_text(standing)}", font=font, fill=(0, 0, 0))
        drawing.text((x2, y), f"{constructor(standing)}", font=font, fill=(0, 0, 0))
        drawing.text((x3, y), f"{points(standing)}", font=font, fill=(0, 0, 0))
        drawing.text((x4, y), f"{wins(standing, round_no)}", font=font, fill=(0, 0, 0))

        y += padding + char_height

    # pylint: enable=invalid-name

    with io.BytesIO() as output:
        img.save(output, format="PNG")
        return output.getvalue()

    raise EncodingError("Unable to encode and write constructor standings image")


class EncodingError(Exception):
    """A generic error to signal that encoding an image from a canvas failed."""
