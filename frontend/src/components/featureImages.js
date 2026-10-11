import dashboardWireframe from "../assets/showcase/dashboard-wireframe.png";
import settingsWireframe from "../assets/showcase/settings-wireframe.png";
import settingsPreview from "../assets/showcase/settings-preview.png";

// Shared by all feature tabs so switching tabs does not change
// the image sequence or restart the corridor animation.
const featureImages = [
  {
    src: dashboardWireframe,
    alt: "Hand-drawn student dashboard wireframe",
  },
  {
    src: settingsPreview,
    alt: "Generated settings interface screenshot",
  },
  {
    src: settingsWireframe,
    alt: "Hand-drawn settings page wireframe",
  },
];

export default featureImages;