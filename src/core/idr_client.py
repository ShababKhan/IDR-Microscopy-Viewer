"""
Live IDR API Client.
"""

import logging
import requests
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

class IDRClient:
    """
    Live HTTP client bridging to the OMERO WebGateway and WebClient APIs
    hosted by the Image Data Resource (IDR).
    """

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        
        # Establishing a guest session (experimenter=-1)
        self.session.get(f"{self.base_url}/webclient/?experimenter=-1")

    def get_screen(self, screen_id: int) -> Optional[Dict[str, Any]]:
        """Get the screen layout."""
        # Simple placeholder for /webclient/api/screens/
        # Not fully needed to jump straight to a plate for this demo
        return {"id": screen_id, "name": f"Screen {screen_id}"}
        
    def get_plate(self, plate_id: int) -> Optional[Dict[str, Any]]:
        """
        Hit the OMERO WebGateway to get the plate grid map
        which contains well coordinates, statuses, and image IDs.
        """
        url = f"{self.base_url}/webgateway/plate/{plate_id}/0/"
        rv = self.session.get(url)
        rv.raise_for_status()
        return {"id": plate_id, "name": f"IDR Plate {plate_id}", "omero_payload": rv.json()}

    def get_image_metadata(self, image_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch full dimensional bounds of the image (sizeZ, sizeT, sizeC).
        """
        url = f"{self.base_url}/webclient/imgData/{image_id}/"
        rv = self.session.get(url)
        rv.raise_for_status()
        raw = rv.json()
        
        if "size" not in raw:
            return None
            
        return {
            "id": image_id,
            "name": raw.get("meta", {}).get("imageName", f"Image {image_id}"),
            "sizeX": raw["size"].get("width", 0),
            "sizeY": raw["size"].get("height", 0),
            "sizeZ": raw["size"].get("z", 1),
            "sizeT": raw["size"].get("t", 1),
            "sizeC": raw["size"].get("c", 1)
        }

    def get_image_data(self, image_id: int, z: int = 0, t: int = 0, high_res: bool = False) -> Optional[bytes]:
        """
        Fetch image bytes. In thumbnail mode, uses render_thumbnail for fast loading.
        In high_res mode, fetches the full-resolution JPEG via render_image with channel
        settings built from imgData (using `&m=c` to enable OMERO color rendering mode).
        """
        if not high_res:
            url = f"{self.base_url}/webclient/render_thumbnail/{image_id}/?size=512"
            rv = self.session.get(url)
            rv.raise_for_status()
            return rv.content
        
        # Fetch channel settings from imgData
        meta_url = f"{self.base_url}/webclient/imgData/{image_id}/"
        meta_rv = self.session.get(meta_url)
        meta_rv.raise_for_status()
        raw = meta_rv.json()
        
        channels = raw.get("channels", [])
        c_parts = []
        for i, ch in enumerate(channels):
            w = ch.get("window", {})
            color = ch.get("color", "FFFFFF")
            start = int(w.get("start", 0))
            end = int(w.get("end", 65535))
            c_parts.append(f"{i+1}|{start}:{end}${color}")
        c_param = ",".join(c_parts)
        
        url = f"{self.base_url}/webgateway/render_image/{image_id}/{z}/{t}/?c={c_param}&m=c"
        rv = self.session.get(url)
        rv.raise_for_status()
        return rv.content
        
    def get_thumbnail(self, image_id: int, size: tuple) -> Optional[bytes]:
        url = f"{self.base_url}/webclient/render_thumbnail/{image_id}/"
        rv = self.session.get(url)
        rv.raise_for_status()
        return rv.content

    # ------------------------------------------------------------------
    # Hierarchy browsing
    # ------------------------------------------------------------------

    def get_study_type(self, study_id: int) -> Optional[str]:
        """
        Determine whether a given ID refers to a Screen or a Project.
        Returns 'screen', 'project', or None if not found.
        """
        r = self.session.get(f"{self.base_url}/api/v0/m/screens/{study_id}/")
        if r.status_code == 200:
            data = r.json().get("data", {})
            return "screen", data.get("Name", f"Screen {study_id}"), data.get("Description", "")
        r = self.session.get(f"{self.base_url}/api/v0/m/projects/{study_id}/")
        if r.status_code == 200:
            data = r.json().get("data", {})
            return "project", data.get("Name", f"Project {study_id}"), data.get("Description", "")
        return None, None, None

    def get_screen_plates(self, screen_id: int) -> List[Dict[str, Any]]:
        """Return list of plates for a given screen."""
        results = []
        url = f"{self.base_url}/api/v0/m/screens/{screen_id}/plates/?limit=500"
        while url:
            r = self.session.get(url)
            r.raise_for_status()
            data = r.json()
            for p in data.get("data", []):
                results.append({"id": p["@id"], "name": p.get("Name", f"Plate {p['@id']}"),
                                 "rows": p.get("Rows", 8), "columns": p.get("Columns", 12)})
            url = data.get("meta", {}).get("next")
        return results

    def get_project_datasets(self, project_id: int) -> List[Dict[str, Any]]:
        """Return list of datasets for a given project."""
        results = []
        url = f"{self.base_url}/api/v0/m/projects/{project_id}/datasets/?limit=500"
        while url:
            r = self.session.get(url)
            r.raise_for_status()
            data = r.json()
            for d in data.get("data", []):
                results.append({"id": d["@id"], "name": d.get("Name", f"Dataset {d['@id']}"),
                                 "child_count": d.get("omero:childCount", 0)})
            url = data.get("meta", {}).get("next")
        return results

    def get_dataset_images(self, dataset_id: int) -> List[Dict[str, Any]]:
        """Return list of images inside a dataset."""
        results = []
        url = f"{self.base_url}/api/v0/m/datasets/{dataset_id}/images/?limit=500"
        while url:
            r = self.session.get(url)
            r.raise_for_status()
            data = r.json()
            for img in data.get("data", []):
                results.append({"id": img["@id"], "name": img.get("Name", f"Image {img['@id']}"),
                                 "thumb_url": f"/webclient/render_thumbnail/{img['@id']}/"})
            url = data.get("meta", {}).get("next")
        return results
        
    def list_screens(self, limit: int = 100) -> List[Dict[str, Any]]:
        return []

    def list_plates(self, screen_id: Optional[int] = None, limit: int = 100) -> List[Dict[str, Any]]:
        return []

    def search_images(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        return []
