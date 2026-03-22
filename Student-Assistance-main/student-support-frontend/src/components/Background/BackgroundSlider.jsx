import { useState, useEffect } from "react";

import img1 from "../../assets/campus1.jpg";
import img2 from "../../assets/campus2.jpg";
import img3 from "../../assets/campus3.jpg";
import img4 from "../../assets/campus4.jpeg";
import img5 from "../../assets/campus5.jpeg";
import img6 from "../../assets/campus6.jpeg";

const images = [img1, img2, img3, img4, img5, img6];

function BackgroundSlider() {

  const [index, setIndex] = useState(0);

  useEffect(() => {

    const interval = setInterval(() => {
      setIndex((prev) => (prev + 1) % images.length);
    }, 4000);

    return () => clearInterval(interval);

  }, []);

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        width: "100vw",
        height: "100vh",

        backgroundImage: `url(${images[index]})`,
        backgroundSize: "cover",
        backgroundPosition: "center center",
        backgroundRepeat: "no-repeat",

        transition: "background-image 1s ease-in-out",

        zIndex: -1
      }}
    />
  );
}

export default BackgroundSlider;