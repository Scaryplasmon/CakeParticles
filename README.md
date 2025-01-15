# 🍰 Cake Particles (❁´◡`❁)
> Transform your particle simulations into keyframed objects with ease

[![Blender Extension](https://img.shields.io/badge/Blender-Extension-orange)](https://extensions.blender.org/add-ons/cake-particles/)
[![Blender Kit](https://img.shields.io/badge/Blender-Kit-green)](https://www.blenderkit.com/asset-gallery-detail/82e87770-6569-4873-bef5-8621a1fecdc9/)
[![GumRoad](https://img.shields.io/badge/GumRoad-pink)](https://scaryplasmon.gumroad.com/l/CakeParticles)
[![Version](https://img.shields.io/badge/Version-4.3-blue)]()

[Demo Video](https://github.com/Scaryplasmon/CakeParticles/assets/90010990/4ff7ebb0-220c-40ba-ae2f-3747e6b46e97)

## 🚀 Key Features
- Bake particle simulations into keyframed animated objects
- Multiple Objects support (Meshes, Grease Pencil, Metaballs, Cameras etc.)
- bake-step (to keyframe only each n frames)
- Collection-based management system
- Full simulation/animation export to FBX

<div align="center">
<img src="https://github.com/user-attachments/assets/63f2d40c-1335-4fd3-837c-b9726f0f2348" width="600">
<img src="https://github.com/user-attachments/assets/1738ad03-257b-4239-ac2d-e0ed2942cb70" width="400">
</div>

## Examples
<div align="center">
<img src="https://github.com/Scaryplasmon/CakeParticles/assets/90010990/be40e1ac-dc8c-4e28-aaa8-f0a6f73378c5" width="600">
</div>

*fbxs exported using cakeParticles*
  
- [Cyberpunk Game VFX](https://skfb.ly/ovBXn)
- [Stylized Animation](https://skfb.ly/o9RPG)

## 📦 Installation
Install directly from the [Official Blender Extension Platform](https://extensions.blender.org/add-ons/cake-particles/)
just drag and drop it into your blender.

## 🆕 Version History

### 4.3 - Latest Release
- ✨ New Collection system for multi-bake management
- 🔄 Re-baking support
- 📝 Streamlined UI with collapsible tips
- 🛠️ Enhanced error handling and UX improvements

### 3.0
- ✅ Blender 4.0 compatibility
- 🎨 Grease Pencil animation randomizer

### 2.5
- 🔧 Enhanced Bake_Step functionality
- ➕ Post-bake frame editing panel
- 🏗️ Improved addon architecture

### 2.1.2
- 🐛 Blender 3.6.2+ compatibility
- ✨ Multiple objects particle baking

### 2.0
- 🎯 BakeStep implementation
- 🎨 Grease Pencil and Metaballs support
- 🔄 Multi-object particle support


## 🔧´FAQ and general tips
For particle rotation to work, ensure the "Dynamic" option is enabled in particle settings.
This is by design, as enabling this by default would penalize performance for all the simulations that don´t need particle rotations (which is the case more often than not).

It also matches Blender's current default settings this way.

If Tackling complex simulations:

I suggest to check your particle simulation before baking, by rendering Cubes as object instance, which perform good and show the particle motion very well.

## 📚 Documentation
- [Comprehensive Guide](https://blenderartists.org/t/cake-particles-bake-your-particles-as-keyframed-objects/1378059)
- [Docs](https://sites.google.com/view/cakeparticlesdocs/home-page)

## 🙏 Acknowledgements
- [StackExchange Community](https://tiny.one/StackExchange)
- [BartSketchfab](https://tiny.one/BartSketchfab)
- [Blender Stack Exchange](https://blender.stackexchange.com/questions/167452/convert-particles-to-animated-mesh-including-existing-armature-animation)

---
<div align="center">
Made with 🎂
</div>
