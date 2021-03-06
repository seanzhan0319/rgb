import os
import numpy as np
import cv2
from scipy.spatial import ConvexHull
import visualize
import trimesh


# find the points from an input image
def getPoints(img):
    # img = pad_image(img)
    height, width, _ = img.shape
    # flip the r and b channels
    points = np.reshape(img, [-1, 3]).copy()
    r = points[:, 0].copy()
    b = points[:, 2].copy()
    points[:, 0] = b
    points[:, 2] = r
    return points, height, width


# build the convex hull in RGB space
def getHull(points):
    hull = ConvexHull(points)
    return hull


# find the barycenter of the convex hull
def getBarycenter(hull):
    points = hull.points
    faces = hull.simplices
    surface_area = hull.area
    v0 = points[faces[:,0]]
    v1 = points[faces[:,1]]
    v2 = points[faces[:,2]]
    centroid = (v0 + v1 + v2)/3
    area = 0.5 * np.linalg.norm(np.cross(v1 - v0, v2 - v0), axis=1).reshape(-1,1)
    total = np.sum(centroid * area, axis=0)/surface_area
    return total


def getRayDirs(barycenter, points):
    diff = points - barycenter
    factor = np.linalg.norm(diff, axis=1, keepdims=True)
    return diff / factor


# get the intersections of each ray from the barycenter to the colors
def computeStrokeDensity(barycenter, ray_d, hull, loc_out_path, H, W):
    num_rays = ray_d.shape[0]
    ray_p = np.repeat(np.reshape(barycenter, (1,-1)), axis=0, repeats=num_rays)
    mesh = trimesh.Trimesh(vertices=hull.points, faces=hull.simplices)
    if os.path.exists(loc_out_path):
        print("loading intersection...")
        f = np.load(loc_out_path, allow_pickle=True)
        loc = f['loc']
        ray_idx = f['ray_idx']
    else:
        print("computing intersection...")
        # note: intersected location does follow the same order as ray_d!
        # each loc corresponds to each ray_idx, ray_idx indexes into ray_d
        loc, ray_idx, _ = mesh.ray.intersects_location(
            ray_origins=ray_p, ray_directions=ray_d)
        np.savez_compressed(loc_out_path, loc=loc, ray_idx=ray_idx)
    print("loaded intersection!")
    new_loc = np.zeros_like(loc)
    for i in range(loc.shape[0]):
        new_loc[ray_idx[i]] = loc[i]
    loc = new_loc
    # numerator = np.linalg.norm(hull.points - ray_p, axis=1, keepdims=True)
    # denominator = np.linalg.norm(ray_p - loc, axis=1, keepdims=True)
    numerator = np.linalg.norm(hull.points - loc, axis=1, keepdims=True)
    denominator = np.linalg.norm(ray_p - loc, axis=1, keepdims=True)
    K = numerator / denominator
    K = np.clip(K, 0, 1)
    K = 1 - K
    K = np.reshape(K, (H, W, 1))
    K = np.repeat(K, repeats=3, axis=-1)
    return K


def get_stroke_density(img, intersect_path):
    points, H, W = getPoints(img)
    hull = getHull(points)
    center = getBarycenter(hull)
    ray_dirs = getRayDirs(center, points)
    return computeStrokeDensity(center, ray_dirs, hull, intersect_path, H, W)


def main():
    VIS = False

    in_path = "./imgs/sample-input.png"
    img = cv2.imread(in_path, cv2.IMREAD_COLOR)
    points, H, W = getPoints(img)
    hull = getHull(points)
    if VIS:
        plt = visualize.show_convex_hull(hull)
        plt.savefig("./tmp/convex_hull_vis.png", bbox_inches='tight', pad_inches=0)
        plt.show()
        plt.close()
    
    # exit(0)
    center = getBarycenter(hull)
    ray_dirs = getRayDirs(center, points)
    K = computeStrokeDensity(center, ray_dirs, hull, "./tmp/intersection.npz", H, W)
    sd_out_path = "./tmp/stroke_density.png"
    cv2.imwrite(sd_out_path, (K * 255).astype(np.uint8))


if __name__ == "__main__":
    main()