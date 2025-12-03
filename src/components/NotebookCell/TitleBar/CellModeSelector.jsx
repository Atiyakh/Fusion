import React from "react";
import {
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  Button,
  HStack,
  Box,
} from "@chakra-ui/react";
import { ChevronDown, Check, Code, Database, Server } from "lucide-react";

const OPTIONS = [
  { id: "python", label: "Python", Icon: Code },
  { id: "sql", label: "SQL", Icon: Database },
  { id: "db-adapter", label: "DB Adapter", Icon: Server },
];

export default function CellModeSelector({ value = "python", onChange = () => {}, size = "md" }) {
  const selected = OPTIONS.find((o) => o.id === value) || OPTIONS[0];

  return (
    <Menu className="cell-mode-selector">
      <MenuButton
        as={Button}
        rightIcon={<ChevronDown size={16} />}
        size={size}
        variant="outline"
        display="inline-flex"
        alignItems="center"
        gap={2}
        /* prevent wrapping and truncate if too long */
        whiteSpace="nowrap"
        overflow="hidden"
        textOverflow="ellipsis"
        minW="0"        /* allows the button to shrink in flex layouts */
        px={3}
      >
        <HStack spacing={2} flex="0 0 auto" whiteSpace="nowrap">
          <selected.Icon size={16} />
          <Box
            as="span"
            fontWeight="semibold"
            whiteSpace="nowrap"
            overflow="hidden"
            textOverflow="ellipsis"
          >
            {selected.label}
          </Box>
        </HStack>
      </MenuButton>

      <MenuList
        /* don't force MenuList to match trigger width; keep items single-line */
        minW="0"
        w="auto"
        whiteSpace="nowrap"
        px={1}
      >
        {OPTIONS.map((opt) => (
          <MenuItem
            key={opt.id}
            onClick={() => onChange(opt.id)}
            justifyContent="space-between"
            px={3}
            whiteSpace="nowrap"
          >
            <HStack spacing={2} flex="0 0 auto" whiteSpace="nowrap">
              <opt.Icon size={16} />
              <Box
                as="span"
                fontWeight="semibold"
                whiteSpace="nowrap"
                overflow="hidden"
                textOverflow="ellipsis"
              >
                {opt.label}
              </Box>
            </HStack>

            {opt.id === value && <Check size={16} />}
          </MenuItem>
        ))}
      </MenuList>
    </Menu>
  );
}
