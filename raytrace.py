import numpy as np
from PIL import Image as im


class Ray:
    def __init__(self, e, s):
        self.e = e
        self.s = s

    def get3DPoint(self, t):
        return self.e + (self.s - self.e) * t


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
        B = 2.0 * np.dot(d, e - c)
        C = np.dot(e - c, e - c) - r * r

        delta = B * B - 4.0 * A * C
        if delta < 0:
            return float("inf")

        t1 = (-B - np.sqrt(delta)) / (2.0 * A)
        t2 = (-B + np.sqrt(delta)) / (2.0 * A)

        vals = [t for t in [t1, t2] if t > 1e-4]
        if len(vals) == 0:
            return float("inf")
        return min(vals)

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
        if t > 1e-4:
            return t
        return float("inf")

    def get_normal(self, p):
        return self.n


class Camera:
    eye = np.array((0.0, 0.0, 0.0))

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
        s = np.array((u, v, -self.f))
        return Ray(self.eye, s)


class HitInformation:
    def __init__(self, obj, p):
        self.Object = obj
        self.p = p


class Scene:
    def __init__(self, camera):
        self.theCamera = camera
        self.light_pos = np.array((180.0, 220.0, 200.0))

        self.scene_objects = [
            Sphere(
                np.array((-90.0, 0.0, -800.0)),
                80.0,
                np.array((255.0, 0.0, 0.0))
            ),
            Sphere(
                np.array((90.0, 0.0, -400.0)),
                80.0,
                np.array((0.0, 255.0, 0.0))
            ),
            Plane(
                np.array((0.0, -120.0, 0.0)),
                np.array((0.0, 1.0, 0.0)),
                np.array((170.0, 170.0, 170.0))
            )
        ]

    def find_intersection(self, ray):
        hit_list = []

        for obj in self.scene_objects:
            t = obj.Intersect(ray)
            if t != float("inf"):
                p = ray.get3DPoint(t)
                hit_list.append(HitInformation(obj, p))

        return hit_list

    def get_closest_hit(self, ray):
        hits = self.find_intersection(ray)
        if len(hits) == 0:
            return None

        best = hits[0]
        best_d = np.linalg.norm(best.p - ray.e)

        for h in hits[1:]:
            d = np.linalg.norm(h.p - ray.e)
            if d < best_d:
                best = h
                best_d = d

        return best

    def in_shadow(self, p, light_dir, light_dist):
        shadow_ray = Ray(p + 0.01 * light_dir, p + light_dir)
        shadow_hit = self.get_closest_hit(shadow_ray)

        if shadow_hit is None:
            return False

        d = np.linalg.norm(shadow_hit.p - p)
        return d < light_dist

    def get_color(self, hit):
        if hit is None:
            return np.array((0.0, 0.0, 0.0))

        obj = hit.Object
        p = hit.p
        n = obj.get_normal(p)
        n = n / np.linalg.norm(n)

        view = self.theCamera.eye - p
        view = view / np.linalg.norm(view)

        to_light = self.light_pos - p
        light_dist = np.linalg.norm(to_light)
        light = to_light / light_dist

        ambient = 0.45 * obj.Color

        shadow = 1.0
        if self.in_shadow(p, light, light_dist):
            shadow = 0.45

        diff_amount = max(0.0, np.dot(n, light))
        diffuse = obj.Color * diff_amount * shadow

        r = 2 * np.dot(n, light) * n - light
        r = r / np.linalg.norm(r)

        spec_amount = max(0.0, np.dot(r, view)) ** 45
        specular = np.array((255.0, 255.0, 255.0)) * spec_amount * shadow * 0.9

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

    hit = scene.get_closest_hit(ray)
    if hit is None:
        return np.array((0.0, 0.0, 0.0))

    local_color = scene.get_color(hit)

    p = hit.p
    n = hit.Object.get_normal(p)
    n = n / np.linalg.norm(n)

    d = ray.s - ray.e
    d = d / np.linalg.norm(d)

    r = d - 2 * np.dot(d, n) * n
    r = r / np.linalg.norm(r)

    # glossy reflection: small blur, not noisy
    reflected_color = np.array((0.0, 0.0, 0.0))
    glossy_samples = 8

    for _ in range(glossy_samples):
        jitter = np.array((
            np.random.uniform(-0.012, 0.012),
            np.random.uniform(-0.012, 0.012),
            np.random.uniform(-0.012, 0.012)
        ))
        glossy_dir = r + jitter
        glossy_dir = glossy_dir / np.linalg.norm(glossy_dir)

        glossy_ray = Ray(p + 0.01 * glossy_dir, p + glossy_dir)
        reflected_color += trace_ray(glossy_ray, scene, depth + 1)

    reflected_color = reflected_color / glossy_samples

    eta = 1.0 / 1.5
    refr_dir = refract(d, n, eta)

    if refr_dir is not None:
        refr_dir = refr_dir / np.linalg.norm(refr_dir)
        refracted_ray = Ray(p + 0.01 * refr_dir, p + refr_dir)
        refracted_color = trace_ray(refracted_ray, scene, depth + 1)
    else:
        refracted_color = np.array((0.0, 0.0, 0.0))

    final_color = 0.72 * local_color + 0.16 * reflected_color + 0.12 * refracted_color
    return np.clip(final_color, 0, 255)


def render_view(camera, scene, width, height):
    camera.I = np.zeros([height, width, 3])

    for i in range(height):
        for j in range(width):
            ray = camera.constructRayThroughPixel(i, j)
            color = trace_ray(ray, scene, 0)
            camera.I[i][j] = color

    return im.fromarray(np.uint8(camera.I))


def main():
    width = 512
    height = 512

    camera = Camera(f=500, nrows=height, ncols=width)

    camera.eye = np.array((0.0, 0.0, 0.0))
    scene = Scene(camera)
    img1 = render_view(camera, scene, width, height)
    img1.save("view1.png")
    img1.show()

    camera.eye = np.array((120.0, 40.0, 0.0))
    scene = Scene(camera)
    img2 = render_view(camera, scene, width, height)
    img2.save("view2.png")
    img2.show()

    camera.eye = np.array((-120.0, 60.0, 0.0))
    scene = Scene(camera)
    img3 = render_view(camera, scene, width, height)
    img3.save("view3.png")
    img3.show()


if __name__ == "__main__":
    main()