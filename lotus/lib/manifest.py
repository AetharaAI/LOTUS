"""Helper method for loading a module manifest"""

async def _load_manifest(self, name: str, manifest_path: Path) -> ModuleMetadata:
    """Load and validate a module manifest"""
    try:
        with open(manifest_path, 'r') as f:
            manifest = yaml.safe_load(f)
            
            if manifest is None:
                self.logger.warning(f"Empty manifest in {name} at {manifest_path}")
                manifest = {}
            elif not isinstance(manifest, dict):
                self.logger.warning(f"Invalid manifest format in {name}. Using defaults.")
                manifest = {}
            
            return ModuleMetadata(
                name=name,
                version=manifest.get("version", "0.0.0"),
                type=manifest.get("type", "capability"),
                priority=manifest.get("priority", "normal"),
                path=manifest_path.parent,
                description=manifest.get("description", ""),
                author=manifest.get("author", ""),
                license=manifest.get("license", "")
            )
            
    except Exception as e:
        self.logger.error(f"Failed to load manifest for {name}: {e}", exc_info=True)
        return ModuleMetadata(
            name=name,
            version="0.0.0",
            type="capability",
            priority="normal",
            path=manifest_path.parent
        )