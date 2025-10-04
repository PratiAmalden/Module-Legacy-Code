import { test, expect } from "@playwright/test";
import { _formatHashtags } from "../components/bloom.mjs";

test.describe("_formatHashtag", () => {
    test("formats only the hashtag part into a link", () => {
        const input = "Let's get some #SwizBiz love!!";
        const result = _formatHashtags(input);
        expect(result).toBe(
          `Let's get some <a href="/hashtag/SwizBiz">#SwizBiz</a> love!!`
        );
    } );
})