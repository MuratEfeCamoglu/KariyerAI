import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it } from "vitest";

import { ChipInput } from "../components/ChipInput.tsx";

function Harness({ initial = [], max = 3 }: { initial?: string[]; max?: number }) {
  const [value, setValue] = useState(initial);
  return <ChipInput label="Beceriler" value={value} onChange={setValue} max={max} />;
}

function type(text: string, key = "Enter") {
  const input = screen.getByLabelText("Beceriler");
  fireEvent.change(input, { target: { value: text } });
  fireEvent.keyDown(input, { key });
}

describe("ChipInput", () => {
  it("Enter ile beceri ekler ve sayacı günceller", () => {
    render(<Harness />);

    type(" Python ");

    expect(screen.getByText("Python")).toBeInTheDocument();
    expect(screen.getByText("1/3")).toBeInTheDocument();
    expect(screen.getByLabelText("Beceriler")).toHaveValue("");
  });

  it("Türkçe büyük/küçük harf farkını yok sayarak tekrarı engeller", () => {
    render(<Harness initial={["İngilizce"]} />);

    type("ingilizce");

    expect(screen.getByText('"ingilizce" zaten ekli')).toBeInTheDocument();
    expect(screen.getByText("1/3")).toBeInTheDocument();
  });

  it("× düğmesiyle beceriyi kaldırır", () => {
    render(<Harness initial={["SQL", "Docker"]} />);

    fireEvent.click(screen.getByRole("button", { name: "SQL kaldır" }));

    expect(screen.queryByText("SQL")).not.toBeInTheDocument();
    expect(screen.getByText("Docker")).toBeInTheDocument();
  });

  it("sınıra ulaşınca girişi kapatır", () => {
    render(<Harness initial={["A", "B", "C"]} />);

    expect(screen.getByLabelText("Beceriler")).toBeDisabled();
  });
});
