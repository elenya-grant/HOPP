from shapely.geometry import Polygon, MultiPolygon, Point, shape, box
import numpy as np

def make_square(area_m2,x0=0.0,y0=0.0):
    site_length = np.sqrt(area_m2)
    center = site_length/2
    y1 = y0 + site_length
    x1 = x0 + site_length
    poly = box(x0,y0,x1,y1)
    verts = [[x0,x0],[x1,y0],[x1,y1],[x0,y1]]
    vertices = np.array([np.array(v) for v in verts])
    return poly, vertices

def make_rectangle(area_m2,aspect_ratio=1.5,x0=0.0,y0=0.0):
    #aspect ratio is width/height
    # width * height = area
    # width = aspect*height
    height = np.sqrt(area_m2/aspect_ratio)
    width = area_m2/height
    x1 = x0 + width
    y1 = y0 + height
    poly = box(x0,y0,x1,y1)
    verts = [[x0,x0],[x1,y0],[x1,y1],[x0,y1]]
    vertices = np.array([np.array(v) for v in verts])
    return poly,vertices

def make_circle(area_m2,deg_diff = 10,x0=0.0,y0=0.0):
    r = np.sqrt(area_m2/np.pi)
    dx = np.deg2rad(deg_diff)
    rads = np.arange(0,2*np.pi,dx)
    x_coords = r*np.cos(rads)
    y_coords = r*np.sin(rads)

    if any(x<x0 for x in x_coords):
        x_diff = [x0-x for x in x_coords if x<x0]
        x_adj = max(x_diff)
        x_points = [x+x_adj for x in x_coords]
    else:
        x_points = [x for x in x_coords]
    if any(y<y0 for y in y_coords):
        y_diff = [y0-y for y in y_coords if y<y0]
        y_adj = max(y_diff)
        y_points = [y+y_adj for y in y_coords]
    else:
        y_points = [y for y in y_coords]

    coords = []
    for x,y in zip(x_points,y_points):
        coords.append([x,y])

    poly = Polygon(coords)
    vertices = np.array([np.array(v) for v in coords])
    return poly, vertices

def make_hexagon(area_m2,x0=0.0,y0=0.0):
    s = np.sqrt(area_m2*(2/(3*np.sqrt(3))))
    rads = np.arange(0,2*np.pi,np.deg2rad(60))
    x_coords = s*np.cos(rads)
    y_coords = s*np.sin(rads)

    if any(x<x0 for x in x_coords):
        x_diff = [x0-x for x in x_coords if x<x0]
        x_adj = max(x_diff)
        x_points = [x+x_adj for x in x_coords]
    else:
        x_points = [x for x in x_coords]
    if any(y<y0 for y in y_coords):
        y_diff = [y0-y for y in y_coords if y<y0]
        y_adj = max(y_diff)
        y_points = [y+y_adj for y in y_coords]
    else:
        y_points = [y for y in y_coords]

    coords = []
    for x,y in zip(x_points,y_points):
        coords.append([x,y])

    vertices = np.array([np.array(v) for v in coords])
    poly = Polygon(coords)
    return poly, vertices

