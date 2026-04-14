import numpy as np
from PIL import Image as im

# -----------------------------
# Ray Class
# -----------------------------
class Ray:
    def __init__(self, e, s):
        self.e = e
        self.s = s

    def get3DPoint(self, t):
        return self.e + (self.s - self.e) * t


# -----------------------------
# Sphere Class
# -----------------------------
class Sphere:
    def __init__(self, c, r, k):
        self.Center = c
        self.Radius = r
        self.Color = k

    def Intersect(self, ray):
        d = ray.s - ray.e
        e = ray.e

        c = self.Center
        r = self.Radius

        A = np.dot(d, d)
        B = 2.0 * np.dot(d, (e - c))
        C = np.dot((e - c), (e - c)) - r * r

        delta = B * B - 4.0 * A * C

        if delta < 0:
            return float("inf")

        t1 = (-B - np.sqrt(delta)) / (2.0 * A)
        t2 = (-B + np.sqrt(delta)) / (2.0 * A)

        t = min(t1, t2)

        if t > 0:
            return t
        return float("inf")

    def get_normal(self, p):
        return (p - self.Center) / np.linalg.norm(p - self.Center)


class Plane:
    def __init__(self, p, n, color):
        self.p = p
        self.n = n / np.linalg.norm(n)
        self.Color = color

    def Intersect(self, ray):
        d = ray.s - ray.e
        denom = np.dot(self.n, d)

        if abs(denom) < 1e-6:
            return float("inf")

        t = np.dot(self.p - ray.e, self.n) / denom

        if t > 0:
            return t
        return float("inf")

    def get_normal(self, p):
        return self.n


# -----------------------------
# Camera Class
# -----------------------------
class Camera:
    eye = np.array((0.0, 0.0, 0.0)).transpose()

    def __init__(self, f, nrows, ncols):
        self.f = f
        self.nrows = nrows
        self.ncols = ncols
        self.I = np.zeros([nrows, ncols, 3])

    def ij2uv(self, i, j):
        u = (j + 0.5) - self.ncols / 2
        v = -(i + 0.5) + self.nrows / 2
        return u, v

    def constructRayThroughPixel(self, i, j):
        u, v = self.ij2uv(i, j)
        s = np.array((u, v, -self.f)).transpose()
        return Ray(self.eye, s)


# -----------------------------
# Hit Info
# -----------------------------
class HitInformation:
    def __init__(self, obj, p):
        self.Object = obj
        self.p = p


# -----------------------------
# Scene Class
# -----------------------------
class Scene:
    light_source_1 = np.array([0, 0, 1])
    light_source_1 = light_source_1 / np.linalg.norm(light_source_1)

    def __init__(self, camera):

        self.theCamera = camera
        objects = []

        # Sphere 1
        objects.append(
            Sphere(
                np.array((-90, 0, -800)),
                80,
                np.array((255, 0, 0))
            )
        )

        # Sphere 2
        objects.append(
            Sphere(
                np.array((90, 0, -400)),
                80,
                np.array((0, 255, 0))
            )
        )

        # Plane (floor)
        p1 = np.array((0, -120, 0))
        n = np.array((0, 1, 0))
        color = np.array((180, 180, 180))

        objects.append(Plane(p1, n, color))

        self.scene_objects = objects

    def find_intersection(self, ray):
        hit_list = []

        for obj in self.scene_objects:
            t = obj.Intersect(ray)
            if t != float("inf"):
                p = ray.get3DPoint(t)
                hit_list.append(HitInformation(obj, p))

        return hit_list

    def get_color(self, hit_list):

        if len(hit_list) == 0:
            return np.array((0, 0, 0))

        hit = hit_list[0]
        obj = hit.Object
        p = hit.p

        n = obj.get_normal(p)
        n = n / np.linalg.norm(n)

        view = self.theCamera.eye - p
        view = view / np.linalg.norm(view)

        ambient = 0.2 * obj.Color

        shadow_total = 0
        samples = 8

        for _ in range(samples):
            offset = np.array((
            np.random.uniform(-0.2, 0.2),
            np.random.uniform(-0.2, 0.2),
            np.random.uniform(-0.2, 0.2)
        ))

        light = self.light_source_1 + offset
        light = light / np.linalg.norm(light)

        shadow_ray = Ray(p + 0.001 * light, p + light)
        shadow_hits = self.find_intersection(shadow_ray)

        blocked = False
        for sh in shadow_hits:
            if np.linalg.norm(sh.p - p) > 1e-3:
                blocked = True
                break

        if not blocked:
            shadow_total += 1

        shadow = shadow_total / samples

        light = self.light_source_1
        light = light / np.linalg.norm(light)

        diffuse = max(0, np.dot(n, light))
        diffuse = obj.Color * diffuse * shadow

        r = 2 * np.dot(n, light) * n - light
        r = r / np.linalg.norm(r)

        spec = max(0, np.dot(r, view)) ** 32
        specular = np.array((255, 255, 255)) * spec * shadow

        color = ambient + diffuse + specular

        return np.clip(color, 0, 255)


def refract(d, n, eta):
    cosi = -np.dot(n, d)
    k = 1 - eta * eta * (1 - cosi * cosi)

    if k < 0:
        return None

    return eta * d + (eta * cosi - np.sqrt(k)) * n

def trace_ray(ray, scene, depth):

    if depth > 3:
        return np.array((0.0, 0.0, 0.0))

    hit_list = scene.find_intersection(ray)

    if len(hit_list) == 0:
        return np.array((0.0, 0.0, 0.0))

    # find closest hit
    closest_hit = hit_list[0]
    for hit in hit_list:
        if np.linalg.norm(hit.p - ray.e) < np.linalg.norm(closest_hit.p - ray.e):
            closest_hit = hit

    local_color = scene.get_color([closest_hit])

    p = closest_hit.p
    n = closest_hit.Object.get_normal(p)
    n = n / np.linalg.norm(n)

    d = ray.s - ray.e
    d = d / np.linalg.norm(d)

    # reflection direction
    r = d - 2 * np.dot(d, n) * n
    r = r / np.linalg.norm(r)

    # new reflected ray
    reflected_ray = Ray(p + 0.001 * r, p + r)

    reflected_color = trace_ray(reflected_ray, scene, depth + 1)

    # mix colors
    # refraction
    eta = 1.0 / 1.5
    refr_dir = refract(d, n, eta)

    if refr_dir is not None:
        refr_dir = refr_dir / np.linalg.norm(refr_dir)
        refracted_ray = Ray(p + 0.001 * refr_dir, p + refr_dir)
        refracted_color = trace_ray(refracted_ray, scene, depth + 1)
    else:
        refracted_color = np.array((0.0, 0.0, 0.0))

    final_color = 0.6 * local_color + 0.2 * reflected_color + 0.2 * refracted_color

    return np.clip(final_color, 0, 255)

# -----------------------------
# MAIN RENDER
# -----------------------------
def main():

    width = 512
    height = 512

    camera = Camera(f=500, nrows=height, ncols=width)
    scene = Scene(camera)

    for i in range(height):
        for j in range(width):

            ray = camera.constructRayThroughPixel(i, j)
            hits = scene.find_intersection(ray)

            color = trace_ray(ray, scene, 0)
            camera.I[i][j] = color

    img = im.fromarray(np.uint8(camera.I))
    img.save("output.png")
    img.show()


# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    main()