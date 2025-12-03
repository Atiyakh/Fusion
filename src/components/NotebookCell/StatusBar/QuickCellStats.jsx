
export default function QuickCellStats() {
    let executionCount = <span style={{ color: "#1433e7ff", fontWeight: "bold" }}>[12]</span>;
    let detailsButton = <span onClick={() => console.log("Test")} style={{
        color: "#1433e7ff", cursor: "pointer",
    }}> details</span>
    let timer = <span style={{ color: "#1433e7ff", fontWeight: "bold" }}>0.000s</span>;
    return <p
        style={{
            fontFamily: `"JetBrains Mono", "Fira Code", monospace`,
            color: "gray",
            display: "flex",
            padding: "12px 12px 8px 12px",
            color: "#444",
        }}
    >In&nbsp;{ executionCount }&nbsp;Cell ran for&nbsp;{ timer }&nbsp;|&nbsp;{ detailsButton }</p>;
}
