import * as React from "react";
import MuckTheDuck from "./MuckTheDuck";
import "./LoadingDuck.css";

const LoadingDuck = () => (
    <>
        {/* <svg width={2000} height={1000} style={{ position: "absolute" }}> */}
        {/* <path
                // id="duckPath"
                d="M0,32L21.8,64C43.6,96,87,160,131,192C174.5,224,218,224,262,192C305.5,160,349,96,393,58.7C436.4,21,480,11,524,48C567.3,85,611,171,655,192C698.2,213,742,171,785,154.7C829.1,139,873,149,916,165.3C960,181,1004,203,1047,192C1090.9,181,1135,139,1178,112C1221.8,85,1265,75,1309,90.7C1352.7,107,1396,149,1418,170.7L1440,192"
                stroke="blue"
                fill="none"
            /> */}
        {/* <line id="duckPath" x1="0" y1="0" x2="100%" y2="0" stroke="black" /> */}
        {/* </svg> */}
        <MuckTheDuck
            id="motion-demo"
            height={50}
            style={{
                marginRight: "5px",
                transform: "scaleX(-1)",
            }}
        />
    </>
);
export default LoadingDuck;
