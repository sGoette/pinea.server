import path from "path";
import HtmlWebpackPlugin from "html-webpack-plugin";
import webpack from "webpack";

// Backend for the dev server. Default: local backend. Example: PINEA_API=http://192.0.2.10:4000 npm run dev:frontend
const API = process.env.PINEA_API || "http://localhost:4000";

// npm run build        -> webpack --mode production  (dist/frontend, served by the backend)
// npm run dev:frontend -> webpack serve --mode development (port 3000, proxies /api to API)
export default (env, argv) => {
  const production = argv.mode === "production";

  return {
    mode: production ? "production" : "development",
    entry: "./frontend/src/index.tsx",
    output: {
      filename: "[name].[contenthash].js",
      path: path.resolve("./dist/frontend"),
      publicPath: "/",
      clean: true,
    },
    resolve: {
      extensions: [".tsx", ".ts", ".js"],
    },
    devtool: "source-map",
    module: {
      rules: [
        {
          test: /\.(ts|js)x?$/,
          exclude: /node_modules/,
          use: [
            {
              loader: "babel-loader",
              options: {
                presets: [
                  "@babel/preset-env",
                  "@babel/preset-react",
                  "@babel/preset-typescript",
                ],
              },
            },
          ],
        },
        {
          test: /\.css$/i,
          use: ["style-loader", "css-loader"],
        },
        {
          test: /\.(png|jpe?g|gif|svg)$/i,
          type: "asset/resource",
        },
      ],
    },
    plugins: [
      new HtmlWebpackPlugin({
        template: "./frontend/public/index.html",
      }),
      new webpack.DefinePlugin({
        // Production: same origin as the page. Dev: the configured backend.
        __WSURL__: JSON.stringify(production ? "/ws" : API.replace(/^http/, "ws") + "/ws"),
      }),
    ],
    devServer: {
      static: "./dist/frontend",
      hot: true,
      allowedHosts: "all",
      historyApiFallback: true,
      port: 3000,
      open: true,
      proxy: [
        {
          context: ["/api"],
          target: API,
          changeOrigin: true,
        },
      ],
    },
  };
};
